from typing import Iterable
from mysql.connector.pooling import MySQLConnectionPool

from src.production.sites.mihoyobbs.base import MArtworkInfo


class Repository:

    # TODO: Too many repositories. Start using inheritance so that
    #       this __init__ doesn't need to look like this everywhere
    def __init__(self, host: str = "127.0.0.1", port: int = 3306, user: str = "", password: str = "",
                 database: str = ""):
        self.sql_pool = MySQLConnectionPool(pool_name="", pool_size=10, pool_reset_session=False, host=host, port=port,
                                            user=user, password=password, database=database)
        self.mihoyo_table = "mihoyobbs"

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

    def save_art_one(self, artwork_info: MArtworkInfo):
        return self.save_art_many([ artwork_info ])

    def save_art_many(self, artwork_info_list: Iterable[MArtworkInfo]):
        query = rf"""
            INSERT INTO `{self.mihoyo_table}` (
                post_id, title, tags, views, likes, replies, forwards, bookmarks, created_at, user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                tags=VALUES(tags),
                views=VALUES(views),
                likes=VALUES(likes),
                replies=VALUES(replies),
                forwards=VALUES(forwards),
                bookmarks=VALUES(bookmarks),
                created_at=VALUES(created_at),
                user_id=VALUES(user_id);
        """
        query_args = tuple(
            [
                a.post_id,
                a.subject,
                a.tags,
                a.Stat.view_num,
                a.Stat.like_num,
                a.Stat.reply_num,
                a.Stat.forward_num,
                a.Stat.bookmark_num,
                a.created_at,
                a.uid,
            ] for a in artwork_info_list
        )
        return self._executemany_and_fetchall(query, query_args)
