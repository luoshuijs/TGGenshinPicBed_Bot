# 参考了miHoYoBBS、Twitter、Pixiv以及现有的数据结构

from src.production.sites.mihoyobbs.base import MArtworkInfo
from src.production.sites.twitter.base import TArtworkInfo


class ArtworkInfoSite:
    bilibili = 1
    mihuyoubbs = 2
    pixiv = 3
    twitter = 4


class Stat:
    def __init__(self, view_num: int = 0, reply_num: int = 0, like_num: int = 0, bookmark_num: int = 0,
                 forward_num: int = 0):
        self.forward_num = forward_num  # 关注数
        self.bookmark_num = bookmark_num  # 收藏数
        self.like_num = like_num  # 喜欢数
        self.reply_num = reply_num  # 回复数
        self.view_num = view_num  # 观看数


class ArtworkInfo:

    def __init__(self, data: [TArtworkInfo, MArtworkInfo] = None):
        self.database_id: int = 0
        self.post_id: int = 0
        self.site: int = 0
        self.title: str = ""
        self.origin_url: str = ""
        self.tags: list = []
        self.stat: Stat = Stat()
        self.info: [TArtworkInfo, MArtworkInfo] = None
        if type(data) == TArtworkInfo:
            self.SetTArtworkInfo(data)

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
        if self.tags.count() == 0:
            return ""
        for tag in self.tags:
            temp_tag = "#%s " % tag
            tags_str += temp_tag
        return tags_str

    def SetTArtworkInfo(self, data: TArtworkInfo = None):
        self.origin_url = "https://twitter.com/i/web/status/%s" % data.tid
        self.site = ArtworkInfoSite.twitter
        self.info = data
        self.title = data.title
        self.tags = data.tags
        self.post_id = data.tid
        self.stat.like_num = data.favorite_count


class ArtworkImage:

    def __init__(self, art_id: int, data: bytes = b""):
        self.art_id = art_id
        self.data = data
