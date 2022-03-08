from mysql.connector.pooling import MySQLConnectionPool

from model.artwork import AuditInfo, ArtworkInfo
from service.base import CreateArtworkAuditInfoFromSQLData


class ServiceRepository:

    def __init__(self, host="127.0.0.1", port=3306, user="", password="", database=""):
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

    def apply_update(self, audit_info: AuditInfo):
        query = rf"""
            INSERT INTO `new_examine` (
                site, connection_id, type, status, reason
            ) VALUES (
                %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                type=VALUES(type),
                status=VALUES(status),
                reason=VALUES(reason);
        """
        query_args = (audit_info.site, audit_info.connection_id, audit_info.type.value,
                      audit_info.status.value, audit_info.reason,)
        return self._execute_and_fetchall(query, query_args)

    def get_audit_info(self, artwork_info: ArtworkInfo) -> AuditInfo:
        query = f"""
                    SELECT site, connection_id, type, status, reason
                    FROM `new_examine`
                    WHERE site=%s AND connection_id=%s;
                """
        query_args = (artwork_info.site, artwork_info.artwork_id)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return AuditInfo(site=artwork_info.site, connection_id=artwork_info.artwork_id)
        audit_info = CreateArtworkAuditInfoFromSQLData(data[0])
        return audit_info
