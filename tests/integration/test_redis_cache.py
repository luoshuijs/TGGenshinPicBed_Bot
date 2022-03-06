import os
import unittest

from service.cache import ServiceCache
from model.artwork import AuditType


class TestPixivService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        redis_config = {
            'host': os.environ.get('REDIS_HOST', default='127.0.0.1'),
            'port': int(os.environ.get('REDIS_PORT', default='6379')),
            'db': int(os.environ.get('REDIS_DATABASE', default='4')),
        }
        sc = ServiceCache(**redis_config)
        cls.sc = sc

    def test_no_op(self):
        pass
    
    def test_get_push_one_should_not_fail_when_empty(self):
        artwork_info, count = self.sc.get_push_one(AuditType.SFW)
        self.assertEqual(artwork_info, None)
        self.assertEqual(count, 0)
