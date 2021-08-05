from typing import Iterable

import aiomysql

from src.model.artwork import AuditStatus, ArtworkInfo


class Repository:

    def __init__(self, sql_config = None):
        self.sql_config = sql_config
        self.sql_pool = None
        self.pixiv_table = "genshin_pixiv"
        self.pixiv_audit_table = "genshin_pixiv_audit"

    async def close(self):
        if self.sql_pool is None:
            return
        pool = self.sql_pool
        pool.close()
        self.sql_pool = None
        await pool.wait_closed()

    async def _get_pool(self):
        if self.sql_pool is None:
            self.sql_pool = await aiomysql.create_pool(**self.sql_config)
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

    async def get_artists_with_multiple_approved_arts(self, num: int) -> Iterable[int]:
        """
        Get user_id of artists with multiple approved art
        :returns: set(4028484, 18177156)
        """
        query = f"""
            SELECT user_id, COUNT(user_id) AS count
            FROM {self.pixiv_audit_table}
            WHERE status=%s OR status=%s
            GROUP BY user_id
            HAVING count>%s;
        """
        query_args = (AuditStatus.PASS.value, AuditStatus.PUSH.value, num)
        result = await self._execute_and_fetchall(query, query_args)
        return set(i[0] for i in result)    # {4028484, 18177156, ...}

    async def save_artwork_many(self, artwork_list: Iterable[ArtworkInfo]) -> int:
        """
        Save artworks into table. Returns affected rows (not the number of inserted work)
        """
        query = f"""
            INSERT INTO `{self.pixiv_table}` (
                illusts_id, title, tags, view_count, like_count, love_count,
                user_id, upload_timestamp
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
        query_args = tuple(
            (a.art_id, a.title, a.tags, a.view_count, a.like_count,
             a.love_count, a.author_id, a.upload_timestamp)
            for a in artwork_list
        )
        return await self._executemany(query, query_args)
