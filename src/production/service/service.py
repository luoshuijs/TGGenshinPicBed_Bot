from typing import Optional, Tuple, Iterable
from src.base.model.newartwork import AuditType, ArtworkInfoSite
from src.base.model.newartwork import ArtworkImage, ArtworkInfo
from src.production.sites.mihoyobbs.interface import ExtractMid
from src.production.sites.mihoyobbs.service import MihoyobbsService
from src.production.sites.twitter.interface import ExtractTid
from src.production.sites.twitter.service import TwitterService
from src.production.sites.pixiv.service import PixivService


class BaseService:
    def __init__(self, twitter: TwitterService, mihoyobbs: MihoyobbsService):
        self.twitter = twitter
        self.mihoyobbs = mihoyobbs

    def get_info(self, url: str) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        """
        :param url: 地址
        :return: ArtworkInfo ArtworkImage: 图片信息 图片地址
        """
        tid = ExtractTid(url)
        if tid is not None:
            return self.twitter.contribute_start(tid)
        post_id = ExtractMid(url)
        if post_id is not None:
            return self.mihoyobbs.contribute_start(post_id)
        return None

    def contribute(self, artwork_info: ArtworkInfo) -> bool:
        if artwork_info.site == ArtworkInfoSite.twitter:
            self.twitter.contribute_confirm(artwork_info)
        elif artwork_info.site == ArtworkInfoSite.mihuyoubbs:
            self.mihoyobbs.contribute_confirm(artwork_info)
        else:
            return False
        return True


class AuditService(BaseService):

    def __init__(self, twitter: TwitterService, mihoyobbs: MihoyobbsService, pixiv: PixivService):
        super().__init__(twitter, mihoyobbs)
        self.twitter = twitter
        self.mihoyobbs = mihoyobbs
        self.pixiv = pixiv

    def audit_start(self, audit_type: AuditType) -> int:
        """
        :param audit_type: 设置审核的类型，并对审核进行初始化
        :return: 审核数量
        """
        # 1. Get from database  从数据库获取到要审核的数据
        self.pixiv.get_art_for_audit(audit_type.value)
