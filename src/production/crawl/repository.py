from typing import Iterable

import aiomysql

from src.base.model.oldartwork import ArtworkInfo
from src.base.model.artist import ArtistCrawlInfo
from src.production.crawl.base import ArtistCrawlUpdate, CreateArtistCrawlInfoFromSQLResult


class Repository:

    def __init__(self, sql_config=None):
        self.sql_config = sql_config
        self.sql_pool = None
        self.pixiv_table = "genshin_pixiv"
        self.pixiv_audit_table = "genshin_pixiv_audit"
        self.pixiv_artist_table = "pixiv_artist"
        self.pixiv_approved_artist_table = "pixiv_approved_artist"

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

    async def get_artists_with_multiple_approved_arts(self, num: int, days_ago: int) -> Iterable[ArtistCrawlInfo]:
        """
        Get user_id of artists with multiple approved art
        获取具有多个已通过插画的画师的用户id
        :returns: [ArtistCrawlInfo(user_id=1713, last_art_id=18324, ...), ...]
        """
        query = f"""
            SELECT user_id, last_art_id, last_crawled_at, approved_art_count
            FROM {self.pixiv_approved_artist_table}
            WHERE approved_art_count >= %s
            AND (last_crawled_at IS NULL OR DATEDIFF(NOW(), last_crawled_at) >= %s);
        """
        query_args = (num, days_ago)
        result = await self._execute_and_fetchall(query, query_args)
        return CreateArtistCrawlInfoFromSQLResult(
            result)  # [ArtistCrawlInfo(user_id=1713, last_art_id=18324, ...), ...]

    async def save_artist_last_crawl(self, user_id: int, last_art_id: int):
        """
        Update artist crawled data.
        更新画师的爬虫数据。
        """
        query = f"""
            INSERT INTO {self.pixiv_artist_table} (
                user_id, last_art_id
            ) VALUES (
                %s, %s
            ) ON DUPLICATE KEY UPDATE
                last_art_id=VALUES(last_art_id),
                last_crawled_at=NOW();
        """
        query_args = (user_id, last_art_id)
        return await self._execute_and_fetchall(query, query_args)

    async def save_artist_last_crawl_many(self, last_crawl_list: Iterable[ArtistCrawlUpdate]) -> int:
        """
        Update artist crawled data. Returns affected rows (not the number of inserted rows)
        更新画师的爬虫数据。
        """
        if len(last_crawl_list) == 0:
            return 0
        query = f"""
            INSERT INTO {self.pixiv_artist_table} (
                user_id, last_art_id
            ) VALUES (
                %s, %s
            ) ON DUPLICATE KEY UPDATE
                last_art_id=VALUES(last_art_id),
                last_crawled_at=NOW();
        """
        query_args = tuple((a.user_id, a.art_id) for a in last_crawl_list)
        return await self._executemany(query, query_args)

    async def save_artwork_many(self, artwork_list: Iterable[ArtworkInfo]) -> int:
        """
        Save artworks into table. Returns affected rows (not the number of inserted rows)
        """
        if len(artwork_list) == 0:
            return 0
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
