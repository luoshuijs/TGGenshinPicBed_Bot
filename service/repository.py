from mysql.connector.pooling import MySQLConnectionPool

from model.artwork import AuditInfo


class AuditRepository:

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
        query_args = (audit_info.site.value, audit_info.connection_id, audit_info.type.value,
                      audit_info.status.value, audit_info.reason,)
        return self._execute_and_fetchall(query, query_args)

