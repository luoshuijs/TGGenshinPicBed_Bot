from contextlib import contextmanager
from typing import Optional, Tuple, Iterable, List
import ujson

from logger import Log
from model.artwork import AuditType, ArtworkInfoSite, AuditInfo, AuditStatus
from model.artwork import ArtworkImage, ArtworkInfo
from model.containers import ArtworkData
from utils.redisaction import RedisUpdate
from service import AuditRepository
from service.cache import ServiceCache
from sites.mihoyobbs.interface import ExtractMId
from sites.mihoyobbs.service import MihoyobbsService
from sites.pixiv.interface import ExtractPId
from sites.twitter.interface import ExtractTId
from sites.twitter.service import TwitterService
from sites.pixiv.service import PixivService


class BaseService:
    def __init__(self, twitter: TwitterService, mihoyobbs: MihoyobbsService, pixiv: PixivService,
                 audit_repository: AuditRepository):
        self.twitter = twitter
        self.mihoyobbs = mihoyobbs
        self.pixiv = pixiv
        self.audit_repository = audit_repository

    def get_info_by_url(self, url: str) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        """
        :param url: 地址
        :return: ArtworkInfo ArtworkImage: 图片信息 图片地址
        """
        art_id = ExtractPId(url)
        if art_id is not None:
            return self.pixiv.get_info_and_image(art_id)
        tid = ExtractTId(url)
        if tid is not None:
            return self.twitter.get_info_and_image(tid)
        post_id = ExtractMId(url)
        if post_id is not None:
            return self.mihoyobbs.get_info_and_image(post_id)
        return None

    def contribute_start(self, url: str) -> ArtworkData:
        art_id = ExtractPId(url)
        if art_id is not None:
            return self.pixiv.contribute_start(art_id)
        tid = ExtractTId(url)
        if tid is not None:
            return self.twitter.contribute_start(tid)
        post_id = ExtractMId(url)
        if post_id is not None:
            return self.mihoyobbs.contribute_start(post_id)
        artwork_data = ArtworkData()
        artwork_data.SetError("网址解析错误")
        return artwork_data

    def contribute(self, artwork_info: ArtworkInfo) -> bool:
        if artwork_info.site == ArtworkInfoSite.PIXIV:
            self.pixiv.contribute_confirm(artwork_info)
        elif artwork_info.site == ArtworkInfoSite.TWITTER:
            self.twitter.contribute_confirm(artwork_info)
        elif artwork_info.site == ArtworkInfoSite.MIHOYOBBS:
            self.mihoyobbs.contribute_confirm(artwork_info)
        else:
            return False
        return True

    def save_artwork_info(self, artwork_info: ArtworkInfo, audit_type: AuditType,
                          audit_status: AuditStatus) -> bool:
        if artwork_info.site == ArtworkInfoSite.PIXIV:
            self.pixiv.contribute_confirm(artwork_info)
        elif artwork_info.site == ArtworkInfoSite.TWITTER:
            self.twitter.contribute_confirm(artwork_info)
        elif artwork_info.site == ArtworkInfoSite.MIHOYOBBS:
            self.mihoyobbs.contribute_confirm(artwork_info)
        else:
            return False
        audit_info = AuditInfo(
            site=artwork_info.site,
            connection_id=artwork_info.post_id,
            type_status=audit_type,
            status=audit_status
        )
        self.audit_repository.apply_update(audit_info)
        return True


class AuditService:

    def __init__(self, twitter: TwitterService, mihoyobbs: MihoyobbsService, pixiv: PixivService,
                 cache: ServiceCache, audit_repository: AuditRepository):
        self.twitter = twitter
        self.mihoyobbs = mihoyobbs
        self.pixiv = pixiv
        self.cache = cache
        self.audit_repository = audit_repository

    def get_info_and_image(self, post_id: int, site: int):
        """
        :param post_id:
        :param site:
        :return: ArtworkInfo ArtworkImage: 图片信息 图片地址
        """
        if site == ArtworkInfoSite.TWITTER.value:
            return self.twitter.get_info_and_image(post_id)
        elif site == ArtworkInfoSite.MIHOYOBBS.value:
            return self.mihoyobbs.get_info_and_image(post_id)
        elif site == ArtworkInfoSite.PIXIV.value:
            return self.pixiv.get_info_and_image(post_id)
        else:
            return None

    def get_cache_key(self, audit_info: AuditInfo):
        arts_dict = {
            "post_id": audit_info.connection_id,
            "site": audit_info.site.value
        }
        return ujson.dumps(arts_dict)

    def apply_update(self, audit_info: AuditInfo):
        return self.audit_repository.apply_update(audit_info)

    def get_audit_info(self, artwork_info: ArtworkInfo):
        if artwork_info.site == ArtworkInfoSite.PIXIV:
            return self.pixiv.PixivRepository.get_audit(artwork_info.post_id)
        pass

    def get_audit(self, audit_type: AuditType):
        update = RedisUpdate.get_audit_one(audit_type)
        data = self.cache.apply_update(update)
        return ujson.loads(data)

    def get_push_one(self, audit_type: AuditType):
        update = RedisUpdate.get_push_one(audit_type)
        data, count = self.cache.apply_update(update)
        if data is None:
            return None, count
        return ujson.loads(data), count

    def audit_start(self, audit_type: AuditType) -> int:
        """
        :param audit_type: 设置审核的类型，并对审核进行初始化
        :return: 审核数量
        """
        # 1. Get from database  从数据库获取到要审核的数据
        artwork_audit_list: List[ArtworkInfo] = []
        artwork_audit_list += self.pixiv.get_art_for_audit(audit_type)
        update = RedisUpdate.add_audit(audit_type, artwork_audit_list)
        return self.cache.apply_update(update)

    def audit_next(self, audit_type: AuditType) -> \
            Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage], AuditInfo]]:
        """
        从审核队列中获取下一个作品
        :param audit_type:
        :return:
        """
        error_message = None
        # 1. Get from redis
        data = self.get_audit(audit_type)
        if data is None:
            if self.cache.audit_size(audit_type) == 0:
                return None
            self.audit_start(audit_type)
            data = self.get_audit(audit_type)
            if data is None:
                return None
        art_data = self.get_info_and_image(**data)
        if art_data is None:
            Log.error("图片获取错误 site:%s post_id:%s" % (data["site"], data["post_id"]))
            audit_info = AuditInfo(
                site=ArtworkInfoSite(data["site"]),
                connection_id=data["post_id"],
                type_status=audit_type,
                status=AuditStatus.REJECT,
                reason="BadRequest"
            )
            self.audit_repository.apply_update(audit_info)
            return None
        artwork_info, artwork_images = art_data
        audit_info = self.get_audit_info(artwork_info)
        return artwork_info, artwork_images, audit_info

    def audit_approve(self, audit_info: AuditInfo, audit_type: AuditType):
        update = RedisUpdate.remove_pending(audit_type, self.get_cache_key(audit_info))
        self.cache.apply_update(update)
        self.apply_update(audit_info.approve(audit_type))

    def audit_reject(self, audit_info: AuditInfo, audit_type: AuditType, reason: str):
        update = RedisUpdate.remove_pending(audit_type, self.get_cache_key(audit_info))
        self.cache.apply_update(update)
        self.apply_update(audit_info.reject(audit_type, reason))

    def audit_cancel(self, audit_info: AuditInfo, audit_type: AuditType):
        update = RedisUpdate.putback_audit(audit_type, self.get_cache_key(audit_info))
        self.cache.apply_update(update)

    def cache_size(self, audit_type: AuditType) -> int:
        return self.cache.audit_size(audit_type)

    def push_start(self, audit_type: AuditType) -> int:
        artwork_audit_list: List[ArtworkInfo] = []
        artwork_audit_list += self.pixiv.get_art_for_push(audit_type)
        update = RedisUpdate.add_push(audit_type, artwork_audit_list)
        return self.cache.apply_update(update)

    def push_next(self, audit_type: AuditType) -> Tuple[ArtworkInfo, Iterable[ArtworkImage], int]:
        # 1. Get from redis
        data, count = self.get_push_one(audit_type)
        if data is None:
            return None
        artwork_info, artwork_images = self.get_info_and_image(**data)
        return artwork_info, artwork_images, count

    @contextmanager
    def push_manager(self, artwork_info: ArtworkInfo):
        yield
        audit_info = self.get_audit_info(artwork_info)
        self.apply_update(audit_info.push())

    def set_art_audit_info(self, artwork_info: ArtworkInfo, info_type: str, data, d_reason=None):
        """
        Set art audit status by art_id
        """
        if info_type not in ["status", "type"]:
            raise ValueError(f"Unknown operation for set_art_audit_info: {info_type}")
        if artwork_info is None:
            return None  # Does not exists in database
        audit_info = self.get_audit_info(artwork_info)
        if info_type == "status":
            audit_info.status = AuditStatus(data)
        elif info_type == "type":
            audit_info.type = AuditType(data)
            if d_reason is not None:
                audit_info.reason = str(d_reason)
        self.apply_update(audit_info)
