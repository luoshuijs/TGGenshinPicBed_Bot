from typing import Iterable

from sites.base.repository import Repository
from sites.mihoyobbs.base import MArtworkInfo, CreateMArtworkFromSQLData


class MihoyobbsRepository(Repository):
    def __init__(self, host: str = "127.0.0.1", port: int = 3306, user: str = "", password: str = "",
                 database: str = ""):
        super().__init__(host, port, user, password, database)

    def get_art_by_artid(self, art_id: int) -> MArtworkInfo:
        query = f"""
            SELECT id, post_id, title, tags, view_num, reply_num, like_num, bookmark_num, forward_num, uid, created_at
            FROM `mihoyobbs`
            WHERE post_id=%s;
        """
        query_args = (art_id,)
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return None
        artwork_info = CreateMArtworkFromSQLData(data[0])
        return artwork_info

    def save_art_one(self, artwork_info: MArtworkInfo):
        return self.save_art_many([artwork_info])

    def save_art_many(self, artwork_info_list: Iterable[MArtworkInfo]):
        query = rf"""
            INSERT INTO mihoyobbs (
                post_id, title, tags, view_num, reply_num, like_num, bookmark_num, forward_num, uid, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                tags=VALUES(tags),
                view_num=VALUES(view_num),
                reply_num=VALUES(reply_num),
                like_num=VALUES(like_num),
                bookmark_num=VALUES(bookmark_num),
                forward_num=VALUES(forward_num)
        """
        query_args = tuple(
            [
                a.post_id,
                a.subject,
                a.GetStringTags(),
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
