# pixivrepo.py
#
# Maintains an out of process shared dependency


from typing import Iterable, Any, Callable
from mysql import connector
from mysql.connector.pooling import MySQLConnectionPool

from src.model.artwork import AuditType, AuditStatus, DataAggregator, ArtworkInfo
from src.production.auditor import ArtworkStatusUpdate



class PixivRepository:

    def __init__(self, host="127.0.0.1", port=3306, user="", password="", database=""):
        self.pixiv_table = "genshin_pixiv"
        self.audit_table = "examine"
        self.pixiv_audit_table = "genshin_pixiv_audit"
        self.pixiv_audit_table_sfw = f"{self.pixiv_audit_table}_sfw"
        self.pixiv_audit_table_nsfw = f"{self.pixiv_audit_table}_nsfw"
        self.pixiv_audit_table_r18 = f"{self.pixiv_audit_table}_r18"
        self.sql_pool = MySQLConnectionPool(pool_name="",
                                            pool_size=10,
                                            pool_reset_session=False,
                                            host=host,
                                            port=port,
                                            user=user,
                                            password=password,
                                            database=database)

    def _execute_and_fetchall(self, query, args):
        with self.sql_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, args)
                result = cur.fetchall()
            conn.commit()
            return result

    def _executemany_and_fetchall(self, query, args):
        with self.sql_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, args)
                result = cur.fetchall()
            conn.commit()
            return result

    def get_art_by_artid(self, art_id: int, result_transformer: Callable[[list], list] = None):
        query = f"""
            SELECT id, illusts_id, title, tags, view_count,
                   like_count, love_count, user_id, upload_timestamp,
                   type, status, reason
            FROM `{self.pixiv_audit_table}`
            WHERE illusts_id=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        if result_transformer:
            data = result_transformer(data)
        return DataAggregator.from_sql_data(data)

    def get_art_for_audit(self, audit_type: AuditType, result_transformer: Callable[[list], list] = None):
        table = ""
        if AuditType(audit_type) == AuditType.SFW:
            table = self.pixiv_audit_table_sfw
        elif AuditType(audit_type) == AuditType.NSFW:
            table = self.pixiv_audit_table_nsfw
        else: # R18
            table = self.pixiv_audit_table_r18
        query = rf"""
            SELECT id, illusts_id, title, tags, view_count,
                   like_count, love_count, user_id, upload_timestamp,
                   type, status, reason
            FROM `{table}`
            WHERE status=%s OR status IS NULL;
        """
        query_args = (AuditStatus.INIT.value,)
        data = self._execute_and_fetchall(query, query_args)
        if result_transformer:
            data = result_transformer(data)
        return DataAggregator.from_sql_data(data)

    def get_art_for_push(self, audit_type: AuditType, result_transformer: Callable[[list], list] = None):
        query = rf"""
            SELECT id, illusts_id, title, tags, view_count,
                   like_count, love_count, user_id, upload_timestamp,
                   type, status, reason
            FROM `{self.pixiv_audit_table}`
            WHERE type=%s AND status=%s;
        """
        query_args = (audit_type.value, AuditStatus.PASS.value,)
        data = self._execute_and_fetchall(query, query_args)
        if result_transformer:
            data = result_transformer(data)
        return DataAggregator.from_sql_data(data)

    def apply_update(self, update: ArtworkStatusUpdate):
        query = rf"""
            INSERT INTO `{self.audit_table}` (
                gp_id, gp_illusts_id, type, status, reason
            ) VALUES (
                %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                gp_id=VALUES(gp_id),
                gp_illusts_id=VALUES(gp_illusts_id),
                type=VALUES(type),
                status=VALUES(status),
                reason=VALUES(reason);
        """
        audit_info = update.audit_info
        query_args = (audit_info.gp_id, audit_info.gp_art_id, update.new_type, update.new_status, update.new_reason)
        return self._execute_and_fetchall(query, query_args)

    def save_art_one(self, artwork_info: ArtworkInfo):
        query = rf"""
            INSERT INTO `{self.pixiv_table}` (
                illusts_id, title, tags, view_count, like_count, love_count, user_id, upload_timestamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                tags=VALUES(tags),
                view_count=VALUES(view_count),
                like_count=VALUES(like_count),
                love_count=VALUES(love_count),
                user_id=VALUES(user_id),
                upload_timestamp=VALUES(upload_timestamp);
        """
        query_args = (
            artwork_info.art_id,
            artwork_info.title,
            artwork_info.tags,
            artwork_info.view_count,
            artwork_info.like_count,
            artwork_info.love_count,
            artwork_info.author_id,
            artwork_info.upload_timestamp,
        )
        return self._execute_and_fetchall(query, query_args)




class Transformer:
    @staticmethod
    def combine(*fn):
        def act(data: Iterable[Iterable[Any]]) -> Iterable[Iterable[Any]]:
            for f in fn:
                data = f(data)
            return data
        return act

    @staticmethod
    def audit_type(audit_type: AuditType, override_if_exists=False):
        audit_type = AuditType(audit_type)
        def map_audit_type(info: Iterable[Any]) -> Iterable[Any]:
            new_type = info[9]
            if not override_if_exists:
                new_type = audit_type if new_type is None else new_type
            else:
                new_type = audit_type
            new_info = [*info]
            new_info[9] = new_type
            return new_info
        def transform_audit_type(data: Iterable[Iterable[Any]]) -> Iterable[Iterable[Any]]:
            return tuple(map_audit_type(info) for info in data)
        return transform_audit_type

    @staticmethod
    def r18_type():
        def map_audit_type(info: Iterable[Any]) -> Iterable[Any]:
            tags = info[3]
            new_type = info[9]
            if "R-18" in tags:
                new_type = AuditType.R18
            new_info = [*info]
            new_info[9] = new_type
            return new_info
        def transform_audit_type(data: Iterable[Iterable[Any]]) -> Iterable[Iterable[Any]]:
            return tuple(map_audit_type(info) for info in data)
        return transform_audit_type
