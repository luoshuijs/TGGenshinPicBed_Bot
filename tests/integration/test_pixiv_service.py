import unittest
import os
import pathlib
from redis import Redis
from mysql.connector import connect
from src.production.pixiv import PixivService


class TestPixivService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 1. Setup connections
        sql_config = {
            "host": os.environ["MYSQL_HOST"],
            "port": os.environ["MYSQL_PORT"],
            "user": os.environ["MYSQL_USER"],
            "password": os.environ["MYSQL_PASSWORD"],
            "database": os.environ["MYSQL_DATABASE"],
        }
        redis_config = {
            "host": os.environ["REDIS_HOST"],
            "port": os.environ["REDIS_PORT"],
            "db": os.environ["REDIS_DATABASE"],
        }
        px_config = {
            "cookie": os.environ["PIXIV_COOKIE"]
        }
        cls.config = {
            "sql_config": sql_config,
            "redis_config": redis_config,
            "px_config": px_config,
        }
        cls.sql_connection = connect(**sql_config)
        cls.redis_connection = Redis(**redis_config)
        sql_file = pathlib.Path(__file__).parent.joinpath("./data.sql").resolve()
        with open(sql_file) as f:
            lines = f.read()
            statements = lines.split(';')
            cls.statements = tuple(s for s in statements if len(s.strip()) > 0)

    @classmethod
    def tearDownClass(cls):
        cls.sql_connection.close()

    def setUp(self):
        self.service = PixivService(**self.config)
        with self.sql_connection.cursor() as cur:
            for statement in self.statements:
                cur.execute(statement)
                self.sql_connection.commit()

    def tearDown(self):
        self.redis_connection.flushall()

    def test_no_op(self):
        pass

    def test_approve_sfw_artwork_does_succeed(self):
        pass

    def test_approve_nsfw_artwork_does_succeed(self):
        pass

    def test_approve_r18_artwork_does_succeed(self):
        pass

    def test_reject_sfw_artwork_does_succeed(self):
        pass

    def test_reject_nsfw_artwork_does_succeed(self):
        pass

    def test_reject_r18_artwork_does_succeed(self):
        pass

    def test_reject_sfw_artwork_for_nsfw_reason_does_succeed(self):
        pass

    def test_reject_sfw_artwork_for_r18_reason_does_succeed(self):
        pass

    def test_reject_nsfw_artwork_for_r18_reason_does_succeed(self):
        pass

    def test_push_sfw_artwork_does_succeed(self):
        pass

    def test_push_nsfw_artwork_does_succeed(self):
        pass

    def test_push_r18_artwork_does_succeed(self):
        pass

    def test_putback_artwork_does_succeed(self):
        pass
