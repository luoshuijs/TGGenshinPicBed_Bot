import unittest
import os
import pathlib
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
        cls.sql_file = pathlib.Path(__file__).parent.joinpath("./data.sql").resolve()
        with open(cls.sql_file) as f:
            lines = f.read()
            statements = lines.split(';')
            cls.statements = tuple(s for s in statements if len(s.strip()) > 0)

    def setUp(self):
        self.service = PixivService(**self.config)
        sql_connection = connect(**self.config["sql_config"])
        with sql_connection.cursor() as cur:
            for statement in self.statements:
                cur.execute(statement)
                sql_connection.commit()

    def test_no_op(self):
        pass

    def test_no_op_2(self):
        pass
