# 参考了miHoYoBBS、Twitter、Pixiv以及现有的数据结构
import pathlib
from enum import Enum

from utils.namemap import NameMap
from sites.mihoyobbs.base import MArtworkInfo
from sites.pixiv.base import PArtworkInfo
from sites.twitter.base import TArtworkInfo

name_map_file = pathlib.Path(__file__).parent.joinpath("../data/namemap.json").resolve()
name_map = NameMap(name_map_file)


class ArtworkInfoSite(Enum):
    NULL = None
    BILIBILI = "bilibili"
    MIHOYOBBS = "mihoyobbs"
    PIXIV = "pixiv"
    TWITTER = "twitter"


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
    def __init__(self, database_id: int = 0, site: ArtworkInfoSite = None, connection_id: int = 0,
                 type_status: AuditType = None, status: AuditStatus = None, reason: str = ""):
        self.reason = reason
        self.site = site
        self.database_id = database_id
        self.connection_id = connection_id
        self.type = type_status
        self.status = status

    def approve(self, audit_type: AuditType):
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

    def __init__(self, data: [TArtworkInfo, MArtworkInfo] = None):
        self.database_id: int = 0  # 数据库ID 未来可能考虑会弃用
        self.post_id: int = 0  # 作品ID
        self.site = ArtworkInfoSite
        self.title: str = ""  # 标题
        self.origin_url: str = ""
        self.site_name: str = ""
        self.tags: list = []
        self.stat: Stat = Stat()
        self.create_timestamp: int = 0
        self.info: [TArtworkInfo, MArtworkInfo] = None
        if type(data) == TArtworkInfo:
            self.SetTArtworkInfo(data)
        elif type(data) == MArtworkInfo:
            self.SetMArtworkInfo(data)
        elif type(data) == PArtworkInfo:
            self.SetPArtworkInfo(data)
        else:
            raise ValueError(f"unknown action type {data}")

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

    def SetTArtworkInfo(self, data: TArtworkInfo = None):
        self.origin_url = f"https://twitter.com/i/web/status/{data.tid}"
        self.site_name = "Twitter"
        self.site = ArtworkInfoSite.TWITTER
        self.info = data
        self.title = data.title
        self.tags = data.tags
        self.post_id = data.tid
        self.stat.like_num = data.favorite_count
        self.create_timestamp = data.created_at

    def SetMArtworkInfo(self, data: MArtworkInfo = None):
        self.origin_url = f"https://bbs.mihoyo.com/ys/article/{data.post_id}"
        self.site_name = "MiHoYoBBS"
        self.site = ArtworkInfoSite.MIHOYOBBS
        self.info = data
        self.title = data.subject
        self.tags = data.tags
        self.post_id = data.post_id
        self.stat = data.Stat
        self.create_timestamp = data.created_at

    def SetPArtworkInfo(self, data: PArtworkInfo):
        self.origin_url = f"https://www.pixiv.net/artworks/{data.art_id}"
        self.site_name = "Pixiv"
        self.site = ArtworkInfoSite.PIXIV
        self.info = data
        self.title = data.title
        self.tags = data.tags
        self.post_id = data.art_id
        self.stat.bookmark_num = data.love_count
        self.stat.like_num = data.like_count
        self.stat.view_num = data.view_count
        self.create_timestamp = data.upload_timestamp


class ArtworkImage:

    def __init__(self, art_id: int, data: bytes = b""):
        self.art_id = art_id
        self.data = data
