# pixivrepo.py
#
# Maintains an out of process shared dependency


import copy
from typing import Iterable, Any
from mysql.connector.pooling import MySQLConnectionPool

from src.base.model.artwork import AuditType, AuditStatus, ArtworkInfo, AuditInfo
from src.production.pixiv.auditor import ArtworkStatusUpdate



def CreateArtworkFromSQLData(data) -> ArtworkInfo:
    (id, art_id, title, tags, view_count, like_count,
            love_count, author_id, upload_timestamp,
            type, status, reason) = data
    audit_info = AuditInfo(0, 0, id, audit_type=type, audit_status=status, audit_reason=reason)
    return ArtworkInfo(id, art_id, title=title, tags=tags,
               view_count=view_count, like_count=like_count,
               love_count=love_count, author_id=author_id,
               upload_timestamp=upload_timestamp,
               audit_info=audit_info)

def CreateArtworkManyFromSQLData(data) -> Iterable[ArtworkInfo]:
    return [CreateArtworkFromSQLData(i) for i in data]


class PixivRepository:

    def __init__(self, host="127.0.0.1", port=3306, user="", password="", database=""):
        self.pixiv_table = "genshin_pixiv"
        self.audit_table = "examine"
        self.pixiv_audit_table = "genshin_pixiv_audit"
        self.pixiv_audit_table_sfw = f"{self.pixiv_audit_table}_sfw"
        self.pixiv_audit_table_nsfw = f"{self.pixiv_audit_table}_nsfw"
        self.pixiv_audit_table_r18 = f"{self.pixiv_audit_table}_r18"
        self.pixiv_approved_artist_table = "pixiv_approved_artist"
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

    def get_art_by_artid(self, art_id: int) -> ArtworkInfo:
        query = f"""
            SELECT id, illusts_id, title, tags, view_count,
                   like_count, love_count, user_id, upload_timestamp,
                   type, status, reason
            FROM `{self.pixiv_audit_table}`
            WHERE illusts_id=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return None
        artwork_info = CreateArtworkFromSQLData(data[0])
        return Transformer.apply(artwork_info)

    def get_art_for_audit(self, audit_type: AuditType) -> Iterable[ArtworkInfo]:
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
            WHERE status=%s OR status IS NULL
            ORDER BY upload_timestamp DESC, love_count ASC;
        """
        query_args = (AuditStatus.INIT.value,)
        data = self._execute_and_fetchall(query, query_args)
        artwork_info_list = CreateArtworkManyFromSQLData(data)
        return Transformer.apply_many(artwork_info_list, audit_type)

    def get_art_for_push(self, audit_type: AuditType) -> Iterable[ArtworkInfo]:
        query = rf"""
            SELECT id, illusts_id, title, tags, view_count,
                   like_count, love_count, user_id, upload_timestamp,
                   type, status, reason
            FROM `{self.pixiv_audit_table}`
            WHERE type=%s AND status=%s;
        """
        query_args = (audit_type.value, AuditStatus.PASS.value,)
        data = self._execute_and_fetchall(query, query_args)
        artwork_info_list = CreateArtworkManyFromSQLData(data)
        return Transformer.apply_many(artwork_info_list, audit_type)

    def apply_update(self, update: ArtworkStatusUpdate):
        query = rf"""
            INSERT INTO `{self.audit_table}` (
                illusts_id, type, status, reason
            ) VALUES (
                %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                type=VALUES(type),
                status=VALUES(status),
                reason=VALUES(reason);
        """
        audit_info = update.audit_info
        query_args = (audit_info.gp_art_id, update.new_type, update.new_status, update.new_reason)
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

    def get_approved_art_count_by_artistid(self, artistid: int) -> int:
        """
        Get number of approved arts by artist id
        """
        query = f"""
            SELECT approved_art_count
            FROM {self.pixiv_approved_artist_table}
            WHERE user_id = %s;
        """
        query_args = (artistid,)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return 0
        approved_art_count, = data
        return approved_art_count


class Transformer:

    class Singular:
        @staticmethod
        def audit_type(info: ArtworkInfo, audit_type: AuditType, override_if_exists=False):
            new_type = AuditType(audit_type)
            audit_type = info.audit_info.audit_type
            if not override_if_exists:
                if audit_type is not None:
                    new_type = audit_type
            else:
                new_type = audit_type
            new_info = copy.deepcopy(info)
            new_info.audit_info.audit_type = new_type
            return info

        @staticmethod
        def initialize_none(info: ArtworkInfo):
            audit_type = info.audit_info.audit_type
            audit_status = info.audit_info.audit_status
            if audit_type is None:
                audit_type = AuditType.SFW
            if audit_status is None:
                audit_status = AuditStatus.INIT
            new_info = copy.deepcopy(info)
            new_info.audit_info.audit_type = audit_type
            new_info.audit_info.audit_status = audit_status
            return new_info

        @staticmethod
        def r18_type(info: ArtworkInfo):
            tags = info.tags
            new_type = info.audit_info.audit_type
            if "R-18" in tags and new_type is None:
                new_type = AuditType.R18
            new_info = copy.deepcopy(info)
            new_info.audit_info.audit_type = new_type
            return new_info

    class Many:
        @staticmethod
        def audit_type(info_list: Iterable[ArtworkInfo], audit_type: AuditType, override_if_exists=False):
            return [Transformer.Singular.audit_type(i, audit_type, override_if_exists) for i in info_list]

        @staticmethod
        def initialize_none(info_list: Iterable[ArtworkInfo]):
            return [Transformer.Singular.initialize_none(i) for i in info_list]

        @staticmethod
        def r18_type(info_list: Iterable[ArtworkInfo]):
            return [Transformer.Singular.r18_type(i) for i in info_list]

    @staticmethod
    def apply(artwork_info: ArtworkInfo, audit_type: AuditType = None, override_if_exists=False):
        t = Transformer.Singular
        artwork_info = t.initialize_none(t.r18_type(artwork_info))
        if audit_type is not None:
            artwork_info = t.audit_type(artwork_info, audit_type, override_if_exists)
        return artwork_info

    @staticmethod
    def apply_many(artwork_list: Iterable[ArtworkInfo], audit_type: AuditType = None, override_if_exists=False):
        t = Transformer.Many
        artwork_list = t.initialize_none(t.r18_type(artwork_list))
        if audit_type is not None:
            artwork_list = t.audit_type(artwork_list, audit_type, override_if_exists)
        return artwork_list
