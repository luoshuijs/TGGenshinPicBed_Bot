from typing import Optional, Tuple, Iterable
import pathlib

from src.base.model.newartwork import AuditType, ArtworkInfoSite
from src.base.utils.namemap import NameMap
from src.base.model.newartwork import ArtworkImage, ArtworkInfo
from src.production.sites.mihoyobbs.interface import MxtractTid
from src.production.sites.mihoyobbs.service import MihoyobbsService
from src.production.sites.twitter.interface import ExtractTid
from src.production.sites.twitter.service import TwitterService


class AuditService:

    def __init__(self, sql_config=None):
        name_map_file = pathlib.Path(__file__).parent.joinpath("../../../data/namemap.json").resolve()
        self.name_map = NameMap(name_map_file)

    def audit_start(self, audit_type: AuditType) -> int:
        """
        :param audit_type: 设置审核的类型，并对审核进行初始化
        :return: 审核数量
        """
        # 1. Get from database  从数据库获取到要审核的数据
        pass


class SendService:
    def __init__(self, sql_config=None):
        name_map_file = pathlib.Path(__file__).parent.joinpath("../../../data/namemap.json").resolve()
        self.name_map = NameMap(name_map_file)
        self.twitter = TwitterService()
        self.mihoyobbs = MihoyobbsService()

    def get_info(self, url: str) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        if "twitter" in url:
            tid = ExtractTid(url)
            if tid is None:
                return None
            return self.twitter.contribute_start(tid)
        elif "mihoyo" in url:
            post_id = MxtractTid(url)
            if post_id is None:
                return None
            return self.mihoyobbs.contribute_start(post_id)
        else:
            pass
        return None

    def contribute(self, artwork_info: ArtworkInfo) -> bool:
        if artwork_info.site == ArtworkInfoSite.twitter:
            self.twitter.contribute_confirm(artwork_info.post_id)

        return True
