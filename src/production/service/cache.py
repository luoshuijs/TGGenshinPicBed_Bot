import time
import ujson
import redis
from enum import Enum
from typing import Iterable


class ServiceCache:
    def __init__(self, host="127.0.0.1", port=6379, db=0):
        self.rdb = redis.Redis(host=host, port=port, db=db)
        self.ttl = 600  # seconds
