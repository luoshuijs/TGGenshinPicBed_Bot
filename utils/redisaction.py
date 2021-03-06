from typing import Iterable
from enum import Enum
from model.artwork import AuditType, ArtworkInfo


class RedisActionType(Enum):
    ADD_AUDIT = "add_audit"
    ADD_PUSH = "add_push"
    GET_AUDIT_ONE = "get_audit_one"
    GET_PUSH_ONE = "get_push_one"
    REM_PENDING = "remove_pending"
    PUTBACK_AUDIT = "putback_audit"


class RedisUpdate:

    def __init__(self, action: RedisActionType, audit_type: AuditType, data=None):
        self.action = action
        self.audit_type = audit_type
        self.data = data

    @classmethod
    def add_audit(cls, audit_type: AuditType, artwork_list: Iterable[ArtworkInfo]):
        return cls(action=RedisActionType.ADD_AUDIT, audit_type=audit_type, data=artwork_list)

    @classmethod
    def add_push(cls, audit_type: AuditType, artwork_list: Iterable[ArtworkInfo]):
        return cls(action=RedisActionType.ADD_PUSH, audit_type=audit_type, data=artwork_list)

    @classmethod
    def get_audit_one(cls, audit_type: AuditType):
        return cls(action=RedisActionType.GET_AUDIT_ONE, audit_type=audit_type)

    @classmethod
    def get_push_one(cls, audit_type: AuditType):
        return cls(action=RedisActionType.GET_PUSH_ONE, audit_type=audit_type)

    @classmethod
    def putback_audit(cls, audit_type: AuditType, art_key: str):
        return cls(action=RedisActionType.PUTBACK_AUDIT, audit_type=audit_type, data=art_key)

    @classmethod
    def remove_pending(cls, audit_type: AuditType, art_key: str):
        return cls(action=RedisActionType.REM_PENDING, audit_type=audit_type, data=art_key)
