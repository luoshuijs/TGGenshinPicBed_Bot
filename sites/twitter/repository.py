from sites.base.repository import Repository
from sites.twitter.base import CreateTArtworkFromSQLData, TArtworkInfo


class TwitterRepository(Repository):
    def __init__(self, host: str = "127.0.0.1", port: int = 3306, user: str = "", password: str = "",
                 database: str = ""):
        super().__init__(host, port, user, password, database)

    def get_art_by_artid(self, art_id: int) -> TArtworkInfo:
        query = f"""
            SELECT id, tid, text, tags,favorite_count, width,
                   height, user_id, created_at
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

    def get_art_for_audit(self) -> list:
        """
        :return: 返回带有作品具体信息的列表
        """
        query = rf"""
                    SELECT tid, type, status, reason
                    FROM `twitter_audit`
                    WHERE status IS NULL or status = 0
                """
        query_args = ()
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return []
        return [i[0] for i in data]