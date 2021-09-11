from mysql.connector.pooling import MySQLConnectionPool

from src.production.sites.twitter.base import CreateTArtworkFromSQLData, TArtworkInfo


class TwitterRepository:
    def __init__(self, host: str = "127.0.0.1", port: int = 3306, user: str = "", password: str = "",
                 database: str = ""):
        self.sql_pool = MySQLConnectionPool(pool_name="", pool_size=10, pool_reset_session=False, host=host, port=port,
                                            user=user, password=password, database=database)

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

    def get_art_by_artid(self, art_id: int) -> TArtworkInfo:
        query = f"""
            SELECT id, tid, text, tags,favorite_count, width,
                   height, uidz, created_at
            FROM `twitter`
            WHERE tid=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return None
        artwork_info = CreateTArtworkFromSQLData(data[0])
        return artwork_info

    def save_art_one(self, artwork_info: TArtworkInfo):
        query = rf"""
            INSERT INTO `twitter` (
                tid, text, tags, favorite_count, width, height, user_id, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                text=VALUES(text),
                tags=VALUES(tags),
                favorite_count=VALUES(favorite_count),
                user_id=VALUES(user_id),
                created_at=VALUES(created_at);
        """
        query_args = (
            artwork_info.tid,
            artwork_info.title,
            artwork_info.GetStringTags(),
            artwork_info.favorite_count,
            artwork_info.width,
            artwork_info.height,
            artwork_info.author_id,
            artwork_info.created_at,
        )
        return self._execute_and_fetchall(query, query_args)