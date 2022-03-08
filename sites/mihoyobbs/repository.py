from typing import Iterable, List

from model.artwork import AuditType, AuditStatus, AuditInfo, AuditCount
from sites.base.repository import Repository, AsyncRepository
from sites.mihoyobbs.base import MArtworkInfo, CreateMArtworkFromSQLData, CreateArtworkAuditInfoFromSQLData


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
                a.uid,
                a.created_at
            ] for a in artwork_info_list
        )
        return self._executemany_and_fetchall(query, query_args)

    def get_art_for_push(self, audit_type: AuditType) -> List[AuditInfo]:
        query = rf"""
            SELECT post_id, type, status, reason
            FROM `mihoyobbs_audit`
            WHERE type=%s AND status=%s;
        """
        query_args = (audit_type.value, AuditStatus.PASS.value,)
        data = self._execute_and_fetchall(query, query_args)
        return [CreateArtworkAuditInfoFromSQLData(i) for i in data]

    def get_audit_count(self, user_id: int) -> AuditCount:
        # 寄
        return AuditCount(user_id=user_id)

    def get_art_for_audit(self) -> List[AuditInfo]:
        """
        :return: 返回带有作品具体信息的列表
        """
        query = rf"""
                    SELECT post_id, type, status, reason
                    FROM `mihoyobbs_audit`
                    WHERE status IS NULL or status = 0
                """
        query_args = ()
        data = self._execute_and_fetchall(query, query_args)
        if len(data) == 0:
            return []
        return [CreateArtworkAuditInfoFromSQLData(i) for i in data]


class AsyncMihoyobbsRepository(AsyncRepository):
    def __init__(self, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "", loop=None):
        super().__init__(mysql_host, mysql_port, mysql_user, mysql_password, mysql_database, loop)

    async def get_art_by_artid(self, art_id: int) -> MArtworkInfo:
        query = f"""
            SELECT id, post_id, title, tags, view_num, reply_num, like_num, bookmark_num, forward_num, uid, created_at
            FROM `mihoyobbs`
            WHERE post_id=%s;
        """
        query_args = (art_id,)
        result = await self._execute_and_fetchall(query, query_args)
        return MArtworkInfo(result)

    async def save_artwork_many(self, artwork_list: List[MArtworkInfo]) -> int:
        if len(artwork_list) == 0:
            return 0
        query = f"""
                    INSERT INTO mihoyobbs (
                        post_id, title, tags, view_num, reply_num, like_num, bookmark_num, forward_num, uid, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    ) ON DUPLICATE KEY UPDATE
                        title=VALUES(title),
                        tags=VALUES(tags),
                        view_num=VALUES(view_num),
                        reply_num=VALUES(reply_num),
                        like_num=VALUES(like_num),
                        bookmark_num=VALUES(bookmark_num),
                        forward_num=VALUES(forward_num);
                """
        query_args = tuple(
            (a.post_id, a.subject, a.GetStringTags(), a.Stat.view_num, a.Stat.reply_num,
             a.Stat.like_num, a.Stat.bookmark_num, a.Stat.forward_num, a.uid, a.created_at)
            for a in artwork_list
        )
        return await self._executemany(query, query_args)
