# pixivcache.py
#
# Maintains an out of process shared dependency


import ujson
import redis
from enum import Enum
from typing import Iterable

from src.production.redisaction import RedisUpdate, RedisActionType
from src.model.artwork import AuditType, ArtworkImage, ArtworkImageFactory, ArtworkInfo


class QueueType(Enum):
    AUDIT   = "audit_keys_queue"
    PENDING = "pending_keys_queue"
    PUSH    = "push_keys_queue"
    DIFF    = "diff_queue"


class QueueName:

    def __init__(self, audit_type: AuditType, key_prefix=""):
        self._key_prefix = key_prefix
        self.audit = self._queue_name(QueueType.AUDIT, audit_type)
        self.pending = self._queue_name(QueueType.PENDING, audit_type)
        self.push = self._queue_name(QueueType.PUSH, audit_type)
        self.diff = self._queue_name(QueueType.DIFF, audit_type)

    def _queue_name(self, queue_type: QueueType, audit_type: AuditType):
        # e.g. "genshin_pixiv:SFW:audit_queue"
        #      "genshin_pixiv:SFW:pending_queue"
        if audit_type == QueueType.DIFF:
            return f"{self._key_prefix}:{queue_type.value}"
        return f"{self._key_prefix}:{audit_type.value}:{queue_type.value}"


class PixivCache:

    def __init__(self, host="127.0.0.1", port=6379, db=0):
        self.rdb = redis.Redis(host=host, port=port, db=db)
        self.ttl = 600 #seconds
        self.key_prefix = "genshin_picbed"
        self.artwork_info = f"{self.key_prefix}:artwork_info"
        self.image_cache = f"{self.key_prefix}:image_cache"

    def _artwork_to_dict(self, artwork_audit_list: Iterable[ArtworkInfo]):
        arts_dict = dict()
        for artwork in artwork_audit_list:
            key = f"{artwork.art_id}"
            arts_dict[key] = artwork.to_json()
        return arts_dict

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

    def add_audit(self, audit_type: AuditType, artwork_audit_list: Iterable[ArtworkInfo]) -> int:
        qname = QueueName(audit_type, self.key_prefix)
        arts_to_add = self._artwork_to_dict(artwork_audit_list)
        if len(arts_to_add) > 0:
            with self.rdb.pipeline(transaction=True) as pipe:
                _, _, art_count, _, _, _ = pipe.sadd(qname.diff, *arts_to_add.keys()) \
                                               .sdiffstore(qname.audit, qname.diff, qname.pending) \
                                               .scard(qname.audit) \
                                               .delete(qname.diff) \
                                               .hmset(self.artwork_info, arts_to_add) \
                                               .expire(self.artwork_info, self.ttl) \
                                               .execute()
                return art_count
        return 0

    def putback_audit(self, audit_type: AuditType, art_key: str):
        qname = QueueName(audit_type, self.key_prefix)
        if not art_key:
            return
        def update_queue(pipe):
            result = pipe.srem(qname.pending, art_key)
            pipe.multi()
            if result == 1:
                pipe.sadd(qname.audit, art_key)
                pipe.expire(qname.pending, self.ttl)
                return 1
            return 0
        return self.rdb.transaction(update_queue, qname.audit, value_from_callable=True)

    def get_audit_one(self, audit_type: AuditType) -> str:
        qname = QueueName(audit_type, self.key_prefix)
        def update_queue(pipe):
            art_key = pipe.srandmember(qname.audit)
            art = None
            if art_key is not None:
                art = pipe.hget(self.artwork_info, art_key)
            pipe.multi()
            if art_key is not None:
                pipe.srem(qname.audit, art_key)
                pipe.sadd(qname.pending, art_key)
                pipe.expire(qname.pending, self.ttl)
            pipe.expire(self.artwork_info, self.ttl)
            return art
        return self.rdb.transaction(update_queue, qname.audit, qname.pending, value_from_callable=True)

    def remove_pending_audit(self, audit_type, art_key: str):
        qname = QueueName(audit_type, self.key_prefix)
        with self.rdb.pipeline(transaction=True) as pipe:
            pipe.srem(qname.pending, art_key) \
                .expire(qname.pending, self.ttl) \
                .execute()

    def add_push(self, audit_type: AuditType, artwork_audit_list: Iterable[ArtworkInfo]) -> int:
        qname = QueueName(audit_type, self.key_prefix)
        arts_to_add = self._artwork_to_dict(artwork_audit_list)
        if len(arts_to_add) > 0:
            with self.rdb.pipeline(transaction=True) as pipe:
                _, art_count, _, _ = pipe.sadd(qname.push, *arts_to_add.keys()) \
                                         .scard(qname.push) \
                                         .hmset(self.artwork_info, arts_to_add) \
                                         .expire(self.artwork_info, self.ttl) \
                                         .execute()
                return art_count
        return 0

    def get_push_one(self, audit_type: AuditType) -> str:
        qname = QueueName(audit_type, self.key_prefix)
        def update_queue(pipe):
            artwork_info = self.artwork_info
            art_key = pipe.srandmember(qname.push)
            count = pipe.scard(qname.push)
            art = None
            if art_key is not None:
                art = pipe.hget(artwork_info, art_key)
            pipe.multi()
            pipe.expire(self.artwork_info, self.ttl)
            if art_key is not None:
                pipe.srem(qname.push, art_key)
                return art, count-1
            return None, count
        return self.rdb.transaction(update_queue, qname.push, value_from_callable=True)

    def _get_artwork_info(self, key: str):
        return self.rdb.hget(self.artwork_info, key)

    def get_images_by_artid(self, art_id: int) -> Iterable[ArtworkImage]:
        key = self._image_key_name_by_art(art_id)
        with self.rdb.pipeline(transaction=True) as pipe:
            data, _ = pipe.get(key).expire(key, self.ttl).execute()
        if data is None:
            return None
        return ArtworkImageFactory.create_from_json(data)

    def save_images_by_artid(self, art_id: int, artwork_images: Iterable[ArtworkImage]):
        key = self._image_key_name_by_art(art_id)
        if any([art.art_id != art_id for art in artwork_images]):
            raise TypeError(f"expected art id {art_id}, but some are incorrect: {artwork_images}")
        data = ujson.dumps([art.to_dict() for art in artwork_images])
        return self.rdb.setex(key, self.ttl, data)

    def _image_key_name_by_art(self, art_id: int):
        return f"{self.image_cache}:{art_id}"

