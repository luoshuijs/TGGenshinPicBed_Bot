from mysql.connector.pooling import MySQLConnectionPool


class Repository:

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
