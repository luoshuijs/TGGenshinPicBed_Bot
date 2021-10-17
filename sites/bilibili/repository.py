from mysql.connector.pooling import MySQLConnectionPool

from sites.base.repository import Repository
from sites.bilibili.base import CreateTArtworkFromSQLData, BArtworkInfo


class TwitterRepository(Repository):
    def __init__(self, host: str = "127.0.0.1", port: int = 3306, user: str = "", password: str = "",
                 database: str = ""):
        super().__init__(host, port, user, password, database)

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