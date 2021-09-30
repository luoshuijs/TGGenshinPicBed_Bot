from mysql.connector.pooling import MySQLConnectionPool

from sites.bilibili.base import CreateTArtworkFromSQLData, BArtworkInfo


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

    def get_art_by_artid(self, art_id: int) -> BArtworkInfo:
        query = f"""
            SELECT id, `dynamic_id`, `description`, `tags`,
             `view`, `like`, `comment`, `repos`, `height`, `width`,
              `uid`, `timestamp`
            FROM `bilibili`
            WHERE `dynamic_id`=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return None
        artwork_info = CreateTArtworkFromSQLData(data[0])
        return artwork_info

    def save_art_one(self, artwork_info: BArtworkInfo):
        query = rf"""
            INSERT INTO `bilibili` (
                `dynamic_id`, `description`, `tags`,
             `view`, `like`, `comment`, `repos`, `height`, `width`,
              `uid`, `timestamp`
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                dynamic_id=VALUES(dynamic_id),
                tags=VALUES(tags),
                view=VALUES(view),
                like=VALUES(like),
                comment=VALUES(comment),
                repos=VALUES(repos)
        """
        query_args = (
            artwork_info.dynamic_id,
            artwork_info.description,
            artwork_info.GetStringTags(),
            artwork_info.view,
            artwork_info.like,
            artwork_info.comment,
            artwork_info.view,
            artwork_info.repos,
            artwork_info.width,
            artwork_info.height,
            artwork_info.uid,
            artwork_info.timestamp,
        )
        return self._execute_and_fetchall(query, query_args)