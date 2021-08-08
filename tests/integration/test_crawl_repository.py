import os
import pathlib
import asyncio
import unittest
import aiomysql
from mysql.connector import connect
from src.production.crawl.repository import Repository
from src.production.crawl.base import ArtistCrawlUpdate
from src.base.model.artwork import ArtworkInfo, AuditInfo, AuditType, AuditStatus
from src.base.model.artist import ArtistCrawlInfo


class TestCrawlRepository(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        # 1. Setup connections
        cls.sql_config = {
            "host": os.environ["MYSQL_HOST"],
            "port": os.environ["MYSQL_PORT"],
            "user": os.environ["MYSQL_USER"],
            "password": os.environ["MYSQL_PASSWORD"],
            "database": os.environ["MYSQL_DATABASE"],
        }
        cls.asql_config = {
            "host": os.environ["MYSQL_HOST"],
            "port": int(os.environ["MYSQL_PORT"]),
            "user": os.environ["MYSQL_USER"],
            "password": os.environ["MYSQL_PASSWORD"],
            "db": os.environ["MYSQL_DATABASE"],
        }
        cls.sql_connection = connect(**cls.sql_config)
        create_file = pathlib.Path(__file__).parent.joinpath("./testdata/create_test_crawl_repository.sql").resolve()
        reset_file = pathlib.Path(__file__).parent.joinpath("./testdata/reset_test_crawl_repository.sql").resolve()
        with open(create_file) as f:
            lines = f.read()
            statements = lines.split(';')
            cls.create_statements = tuple(s for s in statements if len(s.strip()) > 0)
        with open(reset_file) as f:
            lines = f.read()
            statements = lines.split(';')
            cls.reset_statements = tuple(s for s in statements if len(s.strip()) > 0)
        with cls.sql_connection.cursor() as cur:
            for s in cls.create_statements:
                cur.execute(s)
                cls.sql_connection.commit()

    @classmethod
    def tearDownClass(cls):
        cls.sql_connection.close()

    async def asyncSetUp(self):
        self.repo = Repository(sql_config=self.asql_config)
        self.asql_connection = await aiomysql.connect(**self.asql_config)

    async def asyncTearDown(self):
        async with self.asql_connection.cursor() as cur:
            for statement in self.reset_statements:
                await cur.execute(statement)
            await self.asql_connection.commit()
        self.asql_connection.close()
        await self.repo.close()

    async def test_noop(self):
        pass

    async def test_correct_number_of_approved_arts_are_recorded(self):
        # 1. Setup
        data_list = [
            {
                "art_id": 90670263,
                "title": "バーバラ",
                "tags": "#原神#GenshinImpact#Genshin#バーバラ#バーバラ(原神)#水着#海#サマータイムスパークル#原神1000users入り",
                "view_count": 11342,
                "like_count": 2146,
                "love_count": 3632,
                "author_id": 17156250,
                "upload_timestamp": 1624114805,
            },
            {
                "art_id": 90806639,
                "title": "蛍ちゃん",
                "tags": "#原神#GenshinImpact#Genshin#蛍#蛍(原神)#荧#Lumine#水着#原神1000users入り",
                "view_count": 13813,
                "like_count": 2821,
                "love_count": 5163,
                "author_id": 17156250,
                "upload_timestamp": 1624633208,
            },
            {
                "art_id": 90967393,
                "title": "フゥータオ",
                "tags": "#原神#GenshinImpact#Genshin#胡桃#胡桃(原神)#ツインテール#水着#フレアビキニ#原神1000users入り",
                "view_count": 11088,
                "like_count": 2389,
                "love_count": 4165,
                "author_id": 17156250,
                "upload_timestamp": 1625238836,
            },
            {
                "art_id": 90940211,
                "title": "シニョーラ",
                "tags": "#シニョーラ#原神#極上の乳#女の子#GenshinImpact#Genshin#シニョーラ(原神)#Signora",
                "view_count": 5000,
                "like_count": 980,
                "love_count": 1660,
                "author_id": 17156250,
                "upload_timestamp": 1625138558,
            },
        ]
        for data in data_list:
            await self.create_approved_artwork(ArtworkInfo(**data), AuditStatus.PASS)
        # 2. Execute
        result = await self.repo.get_artists_with_multiple_approved_arts(3, 7)
        # 3. Compare
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, 17156250)
        self.assertEqual(result[0].approved_art_count, len(data_list))

    async def test_save_artist_last_crawl_succeeds(self):
        data_list = [
            {
                "art_id": 90670263,
                "title": "バーバラ",
                "tags": "#原神#GenshinImpact#Genshin#バーバラ#バーバラ(原神)#水着#海#サマータイムスパークル#原神1000users入り",
                "view_count": 11342,
                "like_count": 2146,
                "love_count": 3632,
                "author_id": 17156250,
                "upload_timestamp": 1624114805,
            },
            {
                "art_id": 90806639,
                "title": "蛍ちゃん",
                "tags": "#原神#GenshinImpact#Genshin#蛍#蛍(原神)#荧#Lumine#水着#原神1000users入り",
                "view_count": 13813,
                "like_count": 2821,
                "love_count": 5163,
                "author_id": 17156250,
                "upload_timestamp": 1624633208,
            },
            {
                "art_id": 90967393,
                "title": "フゥータオ",
                "tags": "#原神#GenshinImpact#Genshin#胡桃#胡桃(原神)#ツインテール#水着#フレアビキニ#原神1000users入り",
                "view_count": 11088,
                "like_count": 2389,
                "love_count": 4165,
                "author_id": 17156250,
                "upload_timestamp": 1625238836,
            },
            {
                "art_id": 90940211,
                "title": "シニョーラ",
                "tags": "#シニョーラ#原神#極上の乳#女の子#GenshinImpact#Genshin#シニョーラ(原神)#Signora",
                "view_count": 5000,
                "like_count": 980,
                "love_count": 1660,
                "author_id": 17156250,
                "upload_timestamp": 1625138558,
            },
        ]
        for data in data_list:
            await self.create_approved_artwork(ArtworkInfo(**data), AuditStatus.PASS)
        # 2. Execute
        result = await self.repo.save_artist_last_crawl(17156250, 90940211)
        # 3. Compare
        artist = await self.get_approved_artist(17156250)
        self.assertEqual(artist.user_id, 17156250)
        self.assertEqual(artist.last_art_id, 90940211)

    async def test_save_many_artist_last_crawl_succeeds(self):
        # 1. Setup
        data_list = [
            {
                "art_id": 90670263,
                "title": "バーバラ",
                "tags": "#原神#GenshinImpact#Genshin#バーバラ#バーバラ(原神)#水着#海#サマータイムスパークル#原神1000users入り",
                "view_count": 11342,
                "like_count": 2146,
                "love_count": 3632,
                "author_id": 17156250,
                "upload_timestamp": 1624114805,
            },
            {
                "art_id": 90806639,
                "title": "蛍ちゃん",
                "tags": "#原神#GenshinImpact#Genshin#蛍#蛍(原神)#荧#Lumine#水着#原神1000users入り",
                "view_count": 13813,
                "like_count": 2821,
                "love_count": 5163,
                "author_id": 17156250,
                "upload_timestamp": 1624633208,
            },
            {
                "art_id": 90967393,
                "title": "フゥータオ",
                "tags": "#原神#GenshinImpact#Genshin#胡桃#胡桃(原神)#ツインテール#水着#フレアビキニ#原神1000users入り",
                "view_count": 11088,
                "like_count": 2389,
                "love_count": 4165,
                "author_id": 17156250,
                "upload_timestamp": 1625238836,
            },
            {
                "art_id": 90826719,
                "title": "ジン",
                "tags": "#原神#ジン#ジン(原神)#ジン・グンヒルド#水着#海風の夢#原神5000users入り",
                "view_count": 24031,
                "like_count": 5349,
                "love_count": 8718,
                "author_id": 17317073,
                "upload_timestamp": 1624710342,
            },
            {
                "art_id": 90479192,
                "title": "ロサリア",
                "tags": "#ロサリア#原神#罗莎莉亚#原神5000users入り#下着#黒下着",
                "view_count": 18054,
                "like_count": 3737,
                "love_count": 6234,
                "author_id": 17317073,
                "upload_timestamp": 1623406321,
            },
        ]
        for data in data_list:
            await self.create_approved_artwork(ArtworkInfo(**data), AuditStatus.PASS)
        update_list = [
            ArtistCrawlUpdate(17156250, 90940211),
            ArtistCrawlUpdate(17317073, 90479192),
        ]
        # 2. Execute
        result = await self.repo.save_artist_last_crawl_many(update_list)
        # 3. Compare
        artist = await self.get_approved_artist(17156250)
        self.assertEqual(artist.user_id, 17156250)
        self.assertEqual(artist.approved_art_count, 3)
        artist = await self.get_approved_artist(17317073)
        self.assertEqual(artist.user_id, 17317073)
        self.assertEqual(artist.approved_art_count, 2)

    async def get_approved_artist(self, user_id: int) -> ArtistCrawlInfo:
        query = f"""
            SELECT user_id, last_art_id, last_crawled_at, approved_art_count
            FROM pixiv_approved_artist
            WHERE user_id=%s;
        """
        query_args = (user_id,)
        artwork = None
        async with self.asql_connection.cursor() as cur:
            await cur.execute(query, query_args)
            result = await cur.fetchall()
            await self.asql_connection.commit()
            if len(result) == 0:
                return None
            result = result[0]
            artist = ArtistCrawlInfo(
                user_id = result[0],
                last_art_id = result[1],
                last_crawled_at = result[2],
                approved_art_count = result[3],
            )
        return artist

    async def create_approved_artwork(self, artwork_info: ArtworkInfo, audit_status=AuditStatus.PUSH):
        query = f"""
            INSERT INTO `genshin_pixiv` (
                illusts_id, title, tags, view_count, like_count, love_count, user_id, upload_timestamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            );
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
        audit_info = AuditInfo(0, 0, artwork_info.art_id, audit_type=AuditType.SFW, audit_status=audit_status)
        async with self.asql_connection.cursor() as cur:
            await cur.execute(query, query_args)
            await self.create_audit_info(audit_info)
            await self.asql_connection.commit()

    async def create_audit_info(self, audit_info: AuditInfo):
        query = f"""
            INSERT INTO `examine` (
                illusts_id, type, status, reason
            ) VALUES (
                %s, %s, %s, %s
            );
        """
        query_args = (
            audit_info.gp_art_id,
            AuditType(audit_info.audit_type).value if audit_info.audit_type is not None else None,
            AuditStatus(audit_info.audit_status).value if audit_info.audit_status is not None else None,
            audit_info.audit_reason,
        )
        async with self.asql_connection.cursor() as cur:
            await cur.execute(query, query_args)
            await self.asql_connection.commit()
