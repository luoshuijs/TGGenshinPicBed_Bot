from mysql.connector.pooling import MySQLConnectionPool
import aiomysql


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


class AsyncRepository:
    def __init__(self, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "", loop=None):
        self.mysql_database = mysql_database
        self.mysql_password = mysql_password
        self.mysql_user = mysql_user
        self.mysql_port = mysql_port
        self.mysql_host = mysql_host
        self.loop = loop
        self.sql_pool = None

    async def close(self):
        if self.sql_pool is None:
            return
        pool = self.sql_pool
        pool.close()
        self.sql_pool = None
        await pool.wait_closed()

    async def _get_pool(self):
        if self.sql_pool is None:
            self.sql_pool = await aiomysql.create_pool(
                host=self.mysql_host, port=self.mysql_port,
                user=self.mysql_user, password=self.mysql_password,
                db=self.mysql_database, loop=self.loop)
        return self.sql_pool

    async def _executemany(self, query, query_args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sql_cur = await conn.cursor()
            await sql_cur.executemany(query, query_args)
            rowcount = sql_cur.rowcount
            await sql_cur.close()
            await conn.commit()
        return rowcount

    async def _execute_and_fetchall(self, query, query_args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sql_cur = await conn.cursor()
            await sql_cur.execute(query, query_args)
            result = await sql_cur.fetchall()
            await sql_cur.close()
            await conn.commit()
        return result
