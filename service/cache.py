import pipes
import time
import ujson
import redis
from enum import Enum
from typing import Iterable

from utils.redisaction import RedisUpdate, RedisActionType
from model.artwork import AuditType, ArtworkInfo


class QueueType(Enum):
    """
    队列类型
    """
    AUDIT = "audit_keys_queue"
    PENDING = "pending_keys_queue"
    PUSH = "push_keys_queue"
    DIFF = "diff_queue"


class QueueName:
    """
    队列名称 合成
    """

    def __init__(self, audit_type: AuditType, key_prefix=""):
        self._key_prefix = key_prefix
        self.audit = self._queue_name(QueueType.AUDIT, audit_type.value)  # sorted set
        self.pending = self._queue_name(QueueType.PENDING, audit_type.value)  # sorted set
        self.push = self._queue_name(QueueType.PUSH, audit_type.value)  # set
        self.diff = self._queue_name(QueueType.DIFF, audit_type.value)  # sorted set

    def _queue_name(self, queue_type: QueueType, audit_type: AuditType):
        if queue_type == QueueType.DIFF:
            return f"{self._key_prefix}:{queue_type.value}"
        return f"{self._key_prefix}:{audit_type}:{queue_type.value}"


class ServiceCache:

    def __init__(self, host="127.0.0.1", port=6379, db=0):
        self.rdb = redis.Redis(host=host, port=port, db=db)
        self.ttl = 600
        self.key_prefix = "picbed"
        self.image_cache = f"{self.key_prefix}:image_cache"

    def _artwork_to_score_dict(self, artwork_audit_list: Iterable[ArtworkInfo]):
        """
        使用优先级(score)进行排序，对最早的作品进行审核
        :param artwork_audit_list:
        :return:
        """
        arts_score_dict = dict()
        for artwork in artwork_audit_list:
            dicts = {
                "post_id": artwork.post_id,
                "site": artwork.site.value
            }
            key = ujson.dumps(dicts)
            arts_score_dict[key] = artwork.create_timestamp
        return arts_score_dict

    def apply_update(self, update: RedisUpdate):
        if update.action == RedisActionType.ADD_AUDIT:
            return self.add_audit(update.audit_type, update.data)
        elif update.action == RedisActionType.ADD_PUSH:
            return self.add_push(update.audit_type, update.data)
        elif update.action == RedisActionType.GET_AUDIT_ONE:
            return self.get_audit_one(update.audit_type)
        elif update.action == RedisActionType.GET_PUSH_ONE:
            return self.get_push_one(update.audit_type)
        elif update.action == RedisActionType.REM_PENDING:
            return self.remove_pending_audit(update.audit_type, update.data)
        elif update.action == RedisActionType.PUTBACK_AUDIT:
            return self.putback_audit(update.audit_type, update.data)
        else:
            raise ValueError(f"unknown action type {update.action}")

    def audit_size(self, audit_type: AuditType):
        qname = QueueName(audit_type, self.key_prefix)
        return self.rdb.zcard(qname.audit)

    def add_audit(self, audit_type: AuditType, artwork_audit_list: Iterable[ArtworkInfo]) -> int:
        """
        批量添加作品到缓存列表
        :param audit_type:
        :param artwork_audit_list:
        :return:
        """
        qname = QueueName(audit_type, self.key_prefix)
        arts_score = self._artwork_to_score_dict(artwork_audit_list)
        if len(arts_score) > 0:
            def update_queue(pipe: pipes):
                pipe.multi()
                pipe.zadd(qname.audit, arts_score)
                pipe.zcard(qname.audit)

            art_count = self.rdb.transaction(update_queue, qname.audit)[1]
            return art_count
        return 0

    def putback_audit(self, audit_type: AuditType, art_key: str):
        """
        重新添加作品到缓存列表
        :param audit_type:
        :param art_key:
        :return:
        """
        qname = QueueName(audit_type, self.key_prefix)
        if not art_key:
            return

        def update_queue(pipe):
            result = pipe.zrem(qname.pending, art_key)
            pipe.multi()
            if result == 1:
                pipe.zadd(qname.audit, {art_key: int(time.time())})
                pipe.expire(qname.pending, self.ttl)
                return 1
            return 0

        return self.rdb.transaction(update_queue, qname.audit, value_from_callable=True)

    def get_audit_one(self, audit_type: AuditType) -> str:
        qname = QueueName(audit_type, self.key_prefix)

        def update_queue(pipe):
            art_with_score = pipe.zrevrange(qname.audit, 0, 0, withscores=True, score_cast_func=int)
            art_key = art_score = None
            if len(art_with_score) > 0:
                art_key = art_with_score[0][0]
                art_score = art_with_score[0][1]
            pipe.multi()
            if art_key is not None:
                pipe.zrem(qname.audit, art_key)
                pipe.zadd(qname.pending, {art_key: art_score})
                pipe.expire(qname.pending, self.ttl)
            return art_key

        return self.rdb.transaction(update_queue, qname.audit, qname.pending, value_from_callable=True)

    def remove_pending_audit(self, audit_type, art_key: str):
        """
        从缓存列表移除对应作品
        :param audit_type:
        :param art_key:
        :return:
        """
        qname = QueueName(audit_type, self.key_prefix)
        with self.rdb.pipeline(transaction=True) as pipe:
            pipe.zrem(qname.pending, art_key) \
                .expire(qname.pending, self.ttl) \
                .execute()

    def add_push(self, audit_type: AuditType, artwork_audit_list: Iterable[ArtworkInfo]) -> int:
        qname = QueueName(audit_type, self.key_prefix)
        arts_to_add = self._artwork_to_score_dict(artwork_audit_list)
        if len(arts_to_add) > 0:
            with self.rdb.pipeline(transaction=True) as pipe:
                _, art_count = pipe.sadd(qname.push, *arts_to_add.keys()) \
                    .scard(qname.push) \
                    .execute()
                return art_count
        return 0

    def get_push_one(self, audit_type: AuditType) -> str:
        qname = QueueName(audit_type, self.key_prefix)
        def update_queue(pipe):
            art_key = pipe.srandmember(qname.push)
            count = pipe.scard(qname.push)
            pipe.multi()
            pipe.srem(qname.push, art_key)
            if art_key is None:
                return None, count
            return art_key, count - 1
        return self.rdb.transaction(update_queue, qname.push, value_from_callable=True)

    def audit_size(self, audit_type: AuditType):
        qname = QueueName(audit_type, self.key_prefix)
        return self.rdb.zcard(qname.audit)

