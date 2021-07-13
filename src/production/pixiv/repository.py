# pixivrepo.py
#
# Maintains an out of process shared dependency


from mysql import connector
from mysql.connector.pooling import MySQLConnectionPool

from src.model.artwork import AuditType, AuditStatus, DataAggregator, ArtworkInfo
from src.production.auditor import ArtworkStatusUpdate


class PixivRepository:

    def __init__(self, host="127.0.0.1", port=3306, user="", password="", database=""):
        self.pixiv_table = "genshin_pixiv"
        self.audit_table = "examine"
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

    def get_art_by_artid(self, art_id: int):
        query = f"""
            SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count, 
                   gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
                   ad.id, ad.gp_id, ad.gp_illusts_id, ad.type, ad.status, ad.reason
            FROM `{self.pixiv_table}` AS gp
            LEFT OUTER JOIN `{self.audit_table}` AS ad
                ON gp.id=ad.gp_id AND gp.illusts_id=ad.gp_illusts_id
            WHERE gp.illusts_id=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        return DataAggregator.from_sql_data(data)

    def get_art_for_audit(self, audit_type: AuditType):
        condition = "(ad.type=%s AND ad.status=%s)"
        if AuditType(audit_type) != AuditType.R18:
            condition = f"""
                (gp.tags NOT LIKE '%R-18%') AND 
                (ad.gp_id IS NULL OR (ad.type=%s AND ad.status=%s))
            """
        else:
            # R18
            condition = f"""
                (gp.tags LIKE '%R-18') OR
                (ad.gp_id IS NULL OR (ad.type=%s AND ad.status=%s))
            """
        query = rf"""
            SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count, 
                   gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
                   ad.id, ad.gp_id, ad.gp_illusts_id, ad.type, ad.status, ad.reason
            FROM `{self.pixiv_table}` AS gp
            LEFT OUTER JOIN `{self.audit_table}` AS ad
                ON gp.id=ad.gp_id AND gp.illusts_id=ad.gp_illusts_id
            WHERE {condition};
        """
        query_args = (audit_type.value, AuditStatus.INIT.value,)
        data = self._execute_and_fetchall(query, query_args)
        return DataAggregator.from_sql_data(data)

    def get_art_for_push(self, audit_type: AuditType):
        query = rf"""
            SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count, 
                   gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
                   ad.id, ad.gp_id, ad.gp_illusts_id, ad.type, ad.status, ad.reason
            FROM `{self.pixiv_table}` AS gp
            INNER JOIN `{self.audit_table}` AS ad
                ON gp.id=ad.gp_id AND gp.illusts_id=ad.gp_illusts_id
            WHERE ad.type=%s AND ad.status=%s;
        """
        query_args = (audit_type.value, AuditStatus.PASS.value,)
        data = self._execute_and_fetchall(query, query_args)
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
