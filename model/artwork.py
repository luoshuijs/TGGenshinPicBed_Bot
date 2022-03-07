# 参考了miHoYoBBS、Twitter、Pixiv以及现有的数据结构
import os
from enum import Enum
import imghdr
from utils.namemap import NameMap

cur_path = os.path.realpath(os.getcwd())
log_path = os.path.join(cur_path, 'data')
name_map_file = os.path.join(log_path, 'namemap.json')
name_map = NameMap(name_map_file)


class AuditType(Enum):
    NULL = None
    SFW = "SFW"
    NSFW = "NSFW"
    R18 = "R18"


class AuditStatus(Enum):
    NULL = None
    INIT = 0
    PASS = 1
    REJECT = 2
    PUSH = 3


class Stat:
    def __init__(self, view_num: int = 0, reply_num: int = 0, like_num: int = 0, bookmark_num: int = 0,
                 forward_num: int = 0):
        self.forward_num = forward_num  # 关注数
        self.bookmark_num = bookmark_num  # 收藏数
        self.like_num = like_num  # 喜欢数
        self.reply_num = reply_num  # 回复数
        self.view_num = view_num  # 观看数


class AuditInfo:
    def __init__(self, database_id: int = 0, site: str = "", connection_id: int = 0,
                 type_status: AuditType = AuditType.NULL, status: AuditStatus = AuditStatus.NULL, reason: str = ""):
        self.reason = reason
        self.site = site
        self.database_id = database_id
        self.connection_id = connection_id
        self.type = type_status
        self.status = status

    def approve(self, audit_type):
        if self.type == AuditType.NULL:
            self.type = audit_type
        self.status = AuditStatus.PASS
        return self

    def reject(self, audit_type: AuditType, reason: str):
        if audit_type == AuditType.SFW or audit_type == AuditType.NULL:
            if reason == AuditType.NSFW.value:
                self.type = AuditType.NSFW
                self.status = AuditStatus.INIT
            elif reason == AuditType.R18.value:
                self.type = AuditType.R18
                self.status = AuditStatus.INIT
            else:
                self.type = audit_type
                self.status = AuditStatus.REJECT
                self.reason = reason
        elif audit_type == AuditType.NSFW:
            if reason == AuditType.R18.value:
                self.type = AuditType.R18
                self.status = AuditStatus.INIT
            else:
                self.type = audit_type
                self.status = AuditStatus.REJECT
                self.reason = reason
        elif audit_type == AuditType.R18:
            if reason == AuditType.NSFW.value:
                self.type = AuditType.NSFW
                self.status = AuditStatus.INIT
            else:
                self.type = audit_type
                self.status = AuditStatus.REJECT
                self.reason = reason
        else:
            raise ValueError(f"unknown action type {audit_type}")
        return self

    def push(self):
        self.status = AuditStatus.PUSH
        return self


class ArtworkInfo:

    def __init__(self):
        self.user_id: int = 0
        self.artwork_id: int = 0  # 作品ID
        self.site = ""
        self.title: str = ""  # 标题
        self.origin_url: str = ""
        self.site_name: str = ""
        self.tags: list = []
        self.stat: Stat = Stat()
        self.create_timestamp: int = 0
        self.info = None

    def GetStringStat(self) -> str:
        if self.stat is None:
            return ""
        stat_str: str = ""
        if self.stat.view_num != 0:
            stat_str += "View %s " % self.stat.view_num
        if self.stat.like_num != 0:
            stat_str += "Like %s " % self.stat.like_num
        if self.stat.bookmark_num != 0:
            stat_str += "Bookmark %s " % self.stat.bookmark_num
        if self.stat.reply_num != 0:
            stat_str += "Reply %s " % self.stat.reply_num
        return stat_str

    def GetStringTags(self, filter_character_tags: bool = False) -> str:
        tags_str: str = ""
        if len(self.tags) == 0:
            return ""
        for tag in self.tags:
            temp_tag = "#%s " % tag
            tags_str += temp_tag
        if filter_character_tags:
            tags_str = name_map.filter_character_tags(tags_str)
        return tags_str


class ArtworkImage:

    def __init__(self, art_id: int, page: int = 0, is_error: bool = False, data: bytes = b""):
        self.art_id = art_id
        self.data = data
        self.is_error = is_error
        if not is_error:
            self.format: str = imghdr.what(None, self.data)
        self.page = page


class AuditCount:
    def __init__(self, user_id: int = 0, total_count: int = 0, pass_count: int = 0, reject_count: int = 0):
        self.user_id = user_id
        if total_count is None:
            self.total_count = 0
        else:
            self.total_count = total_count
        if pass_count is None:
            self.pass_count = 0
        else:
            self.pass_count = pass_count
        if reject_count is None:
            self.reject_count = 0
        else:
            self.reject_count = reject_count
