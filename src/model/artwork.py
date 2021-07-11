from enum import Enum
from typing import Iterable
import json


class AuditType(Enum):
    SFW  = "SFW"
    NSFW = "NSFW"
    R18  = "R18"


class AuditStatus(Enum):
    INIT   = 0
    PASS   = 1
    REJECT = 2
    PUSH   = 3


class DataAggregator:

    def __init__(self, artwork_data=None, audit_data=None):
        self.artwork_data = artwork_data
        self.audit_data = audit_data

    @classmethod
    def from_sql_data(cls, data):
        return tuple(
            cls(artwork_data=info[:9], audit_data=info[9:]) for info in data
        )



class ArtworkInfo:

    def __init__(self, id, art_id, title="", tags="", view_count=0, like_count=0, love_count=0, author_id=0, upload_timestamp=0, audit_info=None):
        self.id = id
        self.art_id = art_id
        self.title = title
        self.tags = tags
        self.view_count = view_count
        self.like_count = like_count
        self.love_count = love_count
        self.author_id = author_id
        self.upload_timestamp = upload_timestamp
        self.audit_info = audit_info
        if self.audit_info is None:
            self.audit_info = AuditInfo(None, self.id, self.art_id)
        self.audit_info.gp_id = self.id
        self.audit_info.gp_art_id = self.art_id

    @classmethod
    def create_from_sql(cls, result_list, audit_info=None):
        id, art_id, title, tags, view_count, like_count, love_count, author_id, upload_timestamp = result_list
        return cls(id, art_id, title=title, tags=tags,
                   view_count=view_count, like_count=like_count,
                   love_count=love_count, author_id=author_id,
                   upload_timestamp=upload_timestamp,
                   audit_info=audit_info)

    @classmethod
    def create_from_json(cls, data):
        data_dict = json.loads(data)
        audit_info = None
        if data_dict["audit_info"]:
            audit_info = AuditInfo(
                id = data_dict["audit_info"]["id"],
                gp_id = data_dict["audit_info"]["gp_id"],
                gp_art_id = data_dict["audit_info"]["gp_art_id"],
                audit_type = data_dict["audit_info"]["audit_type"],
                audit_status = data_dict["audit_info"]["audit_status"],
                audit_reason = data_dict["audit_info"]["audit_reason"],
            )
        return cls(
            id =               data_dict["id"],
            art_id =           data_dict["art_id"],
            title =            data_dict["title"],
            tags =             data_dict["tags"],
            view_count =       data_dict["view_count"],
            love_count =       data_dict["love_count"],
            like_count =       data_dict["like_count"],
            author_id =        data_dict["author_id"],
            upload_timestamp = data_dict["upload_timestamp"],
            audit_info =       audit_info,
        )

    def to_json(self):
        return json.dumps(self._to_dict())

    def _to_dict(self):
        audit_info = None
        if self.audit_info:
            audit_info = self.audit_info._to_dict()
        return {
            "id":               self.id,
            "art_id":           self.art_id,
            "title":            self.title,
            "tags":             self.tags,
            "view_count":       self.view_count,
            "like_count":       self.like_count,
            "love_count":       self.love_count,
            "author_id":        self.author_id,
            "upload_timestamp": self.upload_timestamp,
            "audit_info":       audit_info,
        }


class AuditInfo:

    def __init__(self, id, gp_id, gp_art_id, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT, audit_reason=""):
        self.id = id
        self.gp_id = gp_id
        self.gp_art_id = gp_art_id
        self.audit_type = audit_type
        self.audit_status = audit_status
        self.audit_reason = audit_reason

    @classmethod
    def create_from_sql(cls, result_list):
        id, gp_id, gp_art_id, audit_type, audit_status, audit_reason = result_list
        return cls(id, gp_id, gp_art_id, audit_type=audit_type,
                   audit_status=audit_status, audit_reason=audit_reason)

    @classmethod
    def create_from_json(cls, data):
        pass

    def to_json(self):
        return json.dumps(self._to_dict())

    def _to_dict(self):
        return {
            "id":           self.id,
            "gp_id":        self.gp_id,
            "gp_art_id":    self.gp_art_id,
            "audit_type":   self.audit_type,
            "audit_reason": self.audit_reason,
            "audit_status": self.audit_status,
        }



class ArtworkFactory:
    @staticmethod
    def create_from_sql(aggregated_data_list: Iterable[DataAggregator]) -> Iterable[ArtworkInfo]:
        result = []
        for data in aggregated_data_list:
            audit_info = AuditInfo.create_from_sql(data.audit_data)
            artwork_info = ArtworkInfo.create_from_sql(data.artwork_data, audit_info=audit_info)
            result.append(artwork_info)
        return result



class ArtworkImage:

    def __init__(self, art_id: int, uri: str = "", data: bytes = b""):
        self.art_id = art_id
        self.uri = uri
        self.data = data

    def to_json(self):
        pass

    def to_dict(seld):
        return {
            "art_id": self.art_id,
            "uri":    self.uri,
            "data":   self.data,
        }

    @classmethod
    def create_from_json(Cls, data):
        if data is None:
            return None
        data_dict = json.loads(data)
        return Cls(data_dict["art_id"], uri=data_dict["uri"], data=data_dict["data"])


class ArtworkImageFactory:
    @staticmethod
    def create_from_json(data) -> Iterable[ArtworkImage]:
        if data is None:
            return []
        data_dict_list = json.loads(data)
        return tuple(Cls(
            data_dict["art_id"],
            uri=data_dict["uri"],
            data=data_dict["data"],
        ) for data_dict in data_dict_list)
