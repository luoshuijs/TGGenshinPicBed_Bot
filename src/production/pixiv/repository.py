# pixivrepo.py
#
# Maintains an out of process shared dependency


from mysql import connector
from mysql.connector.pooling import MySQLConnectionPool

from src.model.artwork import AuditType, AuditStatus, DataAggregator
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
            INNER JOIN `{self.audit_table}` AS ad
                ON gp.id=ad.gp_id AND gp.illusts_id=ad.gp_illusts_id
            WHERE gp.illusts_id=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        return DataAggregator.from_sql_data(data)

    def get_art_for_audit(self, audit_type: AuditType):
        condition = "ad.gp_id IS NULL" if audit_type == AuditType.SFW else "TRUE"
        query = rf"""
            SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count, 
                   gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
                   ad.id, ad.gp_id, ad.gp_illusts_id, ad.type, ad.status, ad.reason
            FROM `{self.pixiv_table}` AS gp
            LEFT OUTER JOIN `{self.audit_table}` AS ad
                ON gp.id=ad.gp_id AND gp.illusts_id=ad.gp_illusts_id
            WHERE {condition} OR (ad.type=%s AND ad.status=%s);
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
        _ = self._execute_and_fetchall(query, query_args)

