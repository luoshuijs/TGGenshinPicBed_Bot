import time
import ujson
import redis
from enum import Enum
from typing import Iterable

from src.base.model.newartwork import ArtworkInfo, AuditType


class ServiceCache:
    def __init__(self, host="127.0.0.1", port=6379, db=0):
        self.rdb = redis.Redis(host=host, port=port, db=db)
        self.ttl = 600  # seconds

    def _artwork_to_dict(self, artwork_audit_list: Iterable[ArtworkInfo]):
        arts_dict = dict()
        for artwork in artwork_audit_list:
            key = f"{artwork.post_id}"
            arts_dict[key] = artwork.__dict__
        return arts_dict

    def _artwork_to_score_dict(self, artwork_audit_list: Iterable[ArtworkInfo]):
        arts_score_dict = dict()
        for artwork in artwork_audit_list:
            key = f"{artwork.post_id}"
            arts_score_dict[key] = artwork.create_timestamp
        return arts_score_dict

    def add_audit(self, audit_type: AuditType, artwork_audit_list: Iterable[ArtworkInfo]) -> int:
        """
        添加多个
        :param audit_type:
        :param artwork_audit_list:
        :return:
        """
