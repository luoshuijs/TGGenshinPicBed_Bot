from mysql.connector.pooling import MySQLConnectionPool
from src.production.sites.pixiv.base import CreateArtworkFromSQLData, PArtworkInfo


class PixivRepository:

    def __init__(self, host="127.0.0.1", port=3306, user="", password="", database=""):
        self.pixiv_table = "genshin_pixiv"
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

    def get_art_by_artid(self, art_id: int) -> PArtworkInfo:
        query = f"""
            SELECT id, illusts_id, title, tags, view_count,
                   like_count, love_count, user_id, upload_timestamp
            FROM `genshin_pixiv`
            WHERE illusts_id=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return None
        artwork_info = CreateArtworkFromSQLData(data[0])
        return artwork_info

    def save_art_one(self, artwork_info: PArtworkInfo):
        query = rf"""
            INSERT INTO `genshin_pixiv` (
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
