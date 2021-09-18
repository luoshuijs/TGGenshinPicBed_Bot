# 参考了miHoYoBBS、Twitter、Pixiv以及现有的数据结构
from enum import Enum
from src.production.sites.mihoyobbs.base import MArtworkInfo
from src.production.sites.twitter.base import TArtworkInfo


class ArtworkInfoSite(Enum):
    bilibili = 1
    mihuyoubbs = 2
    pixiv = 3
    twitter = 4


class AuditType(Enum):
    SFW = "SFW"
    NSFW = "NSFW"
    R18 = "R18"


class AuditStatus(Enum):
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
    """
    审核信息
    """

    def __init__(self, database_id: int = 0, site: int = 0, connection_id: int = 0, type_status: int = 0,
                 reason: str = ""):
        self.reason = reason
        self.site = site
        self.database_id = database_id
        self.connection_id = connection_id
        self.type = type_status


class ArtworkInfo:

    def __init__(self, data: [TArtworkInfo, MArtworkInfo] = None):
        self.database_id: int = 0  # 数据库ID 未来可能考虑会弃用
        self.post_id: int = 0  # 作品ID
        self.site: int = 0  # 归属网站，见ArtworkInfoSite
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
        else:
            pass

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

    def GetStringTags(self) -> str:
        tags_str: str = ""
        if len(self.tags) == 0:
            return ""
        for tag in self.tags:
            temp_tag = "#%s " % tag
            tags_str += temp_tag
        return tags_str

    def SetTArtworkInfo(self, data: TArtworkInfo = None):
        self.origin_url = "https://twitter.com/i/web/status/%s" % data.tid
        self.site_name = "Twitter"
        self.site = ArtworkInfoSite.twitter
        self.info = data
        self.title = data.title
        self.tags = data.tags
        self.post_id = data.tid
        self.stat.like_num = data.favorite_count
        self.create_timestamp = data.created_at

    def SetMArtworkInfo(self, data: MArtworkInfo = None):
        self.origin_url = "https://bbs.mihoyo.com/ys/article/%s" % data.post_id
        self.site_name = "MiHoYoBBS"
        self.site = ArtworkInfoSite.mihuyoubbs
        self.info = data
        self.title = data.subject
        self.tags = data.tags
        self.post_id = data.post_id
        self.stat = data.Stat
        self.create_timestamp = data.created_at


class ArtworkImage:

    def __init__(self, art_id: int, data: bytes = b""):
        self.art_id = art_id
        self.data = data
