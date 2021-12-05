import unittest

from logger import Log
from sites import SiteManager


class MyTestCase(unittest.TestCase):
    def test_something(self):
        Log.info("正在测试网站管理器")
        manager = SiteManager()
        manager.load()
        Log.info("网站管理器加载成功")
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
