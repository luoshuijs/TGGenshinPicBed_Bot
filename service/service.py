from contextlib import contextmanager
from typing import Tuple, Iterable, List
import ujson

from logger import Log
from model.artwork import AuditType, AuditInfo, AuditStatus, AuditCount
from model.artwork import ArtworkInfo
from model.containers import ArtworkData, ArtworkAuditData, ArtworkPushData
from model.helpers import parse_artwork_data, parse_artwork_audit_data, parse_artwork_push_data
from service.cache import ServiceCache
from service.repository import AuditRepository
from utils.redisaction import RedisUpdate


class SiteService:

    def __init__(self) -> None:
        self.SiteClassHandlers = []
        self.BaseSizeHandlers = []
        self.sql_config: dict = {}
        self.redis_config: dict = {}
        self.pixiv_cookie: str = ""
        self.audit_repository = None
        self.cache = None

    def set_handlers(self, handlers):
        self.BaseSizeHandlers = handlers

    def set_config(self, sql_config: dict = None, redis_config: dict = None, **args):
        self.sql_config = sql_config
        self.redis_config = redis_config
        self.pixiv_cookie: str = args.get('pixiv_cookie', "")

    def load(self):
        self.audit_repository: AuditRepository = AuditRepository(**self.sql_config)
        self.cache: ServiceCache = ServiceCache(**self.redis_config)
        for handler in self.BaseSizeHandlers:
            handler_size = handler[0]
            handler_module_name = handler[1]
            handler_call = handler[2]
            if "Service" in handler_module_name:
                if callable(handler_call):
                    self.SiteClassHandlers.append((
                        handler_size,
                        handler_call(sql_config=self.sql_config, pixiv_cookie=self.pixiv_cookie)
                    ))
                Log.info(f"{handler_size} 网站 {handler_module_name} 模块 加载成功")

    def Extract(self, url: str) -> [str, int]:
        for handler in self.BaseSizeHandlers:
            handler_size = handler[0]
            handler_module_name = handler[1]
            handler_call = handler[2]
            if "Extract" in handler_module_name:
                if callable(handler_call):
                    artwork_id = handler_call(url)
                    if artwork_id is not None:
                        return handler_size, artwork_id
        return "", 0

    def get_artwork_info_and_image(self, site: str, post_id: int) -> ArtworkData:
        for handler in self.SiteClassHandlers:
            handler_size = handler[0]
            handler_call = handler[1]
            if handler_size.lower() == site.lower():
                if hasattr(handler_call, "get_artwork_info_and_image"):
                    return handler_call.get_artwork_info_and_image(post_id)
        raise ValueError("SiteService Function Not Find")

    def get_info_by_url(self, url: str) -> ArtworkData:
        size_name, artwork_id = self.Extract(url)
        if size_name == "":
            return parse_artwork_data(error_message="不支持")
        return self.get_artwork_info_and_image(size_name, artwork_id)

    def contribute(self, artwork_info: ArtworkInfo) -> ArtworkData:
        for handler in self.SiteClassHandlers:
            handler_size = handler[0]
            handler_call = handler[1]
            if handler_size.lower() == artwork_info.site.lower():
                if hasattr(handler_call, "contribute"):
                    return handler_call.contribute(artwork_info)
        raise ValueError("SiteService Function Not Find")

    def save_artwork_info(self, artwork_info: ArtworkInfo, audit_type: AuditType,
                          audit_status: AuditStatus) -> bool:
        self.contribute(artwork_info)
        audit_info = AuditInfo(
            site=artwork_info.site,
            connection_id=artwork_info.artwork_id,
            type_status=audit_type,
            status=audit_status
        )
        self.audit_repository.apply_update(audit_info)
        return True

    def get_audit_count(self, artwork_info: ArtworkInfo) -> AuditCount:
        for handler in self.SiteClassHandlers:
            handler_size = handler[0]
            handler_call = handler[1]
            if handler_size.lower() == artwork_info.site.lower():
                if hasattr(handler_call, "repository"):
                    if hasattr(handler_call.repository, "get_audit_count"):
                        return handler_call.repository.get_audit_count(artwork_info.user_id)
        raise ValueError("SiteService Function Not Find")

    def contribute_start(self, url: str) -> ArtworkData:
        size_name, artwork_id = self.Extract(url)
        if size_name == "":
            return parse_artwork_data(error_message="不支持该网站")
        for handler in self.SiteClassHandlers:
            handler_size = handler[0]
            handler_call = handler[1]
            if handler_size.lower() == size_name.lower():
                if hasattr(handler_call, "contribute_start"):
                    return handler_call.contribute_start(artwork_id)
        raise ValueError("SiteService Function Not Find")

    def get_audit_info(self, artwork_info: ArtworkInfo) -> AuditInfo:
        for handler in self.SiteClassHandlers:
            handler_size = handler[0]
            handler_call = handler[1]
            if handler_size.lower() == artwork_info.site.lower():
                if hasattr(handler_call, "repository"):
                    if hasattr(handler_call.repository, "get_audit_info"):
                        return handler_call.repository.get_audit_info(artwork_info.artwork_id)
        raise ValueError("SiteService Function Not Find")

    def get_art_for_audit(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        artwork_info_list: list = []
        for handler in self.SiteClassHandlers:
            handler_call = handler[1]
            try:
                if hasattr(handler_call, "get_art_for_audit"):
                    artwork_info_list += handler_call.get_art_for_audit(audit_type)
            except AttributeError:
                pass
        return artwork_info_list

    def get_art_for_push(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        artwork_info_list: list = []
        for handler in self.SiteClassHandlers:
            handler_call = handler[1]
            try:
                if hasattr(handler_call, "get_art_for_push"):
                    artwork_info_list += handler_call.get_art_for_push(audit_type)
            except AttributeError:
                pass
        return artwork_info_list


class AuditService:

    def __init__(self, service: SiteService):
        self.service = service
        self.cache: ServiceCache = service.cache
        self.audit_repository: AuditRepository = service.audit_repository

    def get_cache_key(self, audit_info: AuditInfo):
        arts_dict = {
            "post_id": audit_info.connection_id,
            "site": audit_info.site
        }
        return ujson.dumps(arts_dict)

    def get_artwork_info_and_image(self, site: str, post_id: int) -> ArtworkData:
        return self.service.get_artwork_info_and_image(site, post_id)

    def apply_update(self, audit_info: AuditInfo):
        return self.audit_repository.apply_update(audit_info)

    def get_audit_info(self, artwork_info: ArtworkInfo) -> AuditInfo:
        return self.service.get_audit_info(artwork_info)

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
        artwork_audit_list = self.service.get_art_for_audit(audit_type)
        update = RedisUpdate.add_audit(audit_type, artwork_audit_list)
        return self.cache.apply_update(update)

    def audit_next(self, audit_type: AuditType) -> ArtworkAuditData:
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
                return parse_artwork_audit_data(error_message="缓存错误")
            self.audit_start(audit_type)
            data = self.get_audit(audit_type)
            if data is None:
                return parse_artwork_audit_data(error_message="缓存错误")
        art_data = self.get_artwork_info_and_image(**data)
        if art_data.is_error:
            Log.error("图片获取错误 site:%s post_id:%s" % (data["site"], data["post_id"]))
            audit_info = AuditInfo(
                site=data["site"],
                connection_id=data["post_id"],
                type_status=audit_type,
                status=AuditStatus.REJECT,
                reason="BadRequest"
            )
            self.audit_repository.apply_update(audit_info)
            return parse_artwork_audit_data(error_message=art_data.message)
        audit_info = self.get_audit_info(art_data.artwork_info)
        return parse_artwork_audit_data(art_data.artwork_info, art_data.artwork_image, audit_info)

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
        artwork_audit_list = self.service.get_art_for_push(audit_type)
        update = RedisUpdate.add_push(audit_type, artwork_audit_list)
        return self.cache.apply_update(update)

    def push_next(self, audit_type: AuditType) -> ArtworkPushData:
        # 1. Get from redis
        data, count = self.get_push_one(audit_type)
        if data is None:
            Log.error("获取缓存数据失败 count:%s" % count)
            return parse_artwork_push_data(count=count, error_message="获取缓存数据失败", status_code=67144)
        artwork_data = self.get_artwork_info_and_image(**data)
        if artwork_data.is_error:
            Log.error("图片获取错误 site:%s post_id:%s" % (data["site"], data["post_id"]))
            audit_info = AuditInfo(
                site=data["site"],
                connection_id=data["post_id"],
                type_status=audit_type,
                status=AuditStatus.REJECT,
                reason="BadRequest"
            )
            self.audit_repository.apply_update(audit_info)
            return parse_artwork_push_data(error_message="获取当前图片失败")
        return parse_artwork_push_data(artwork_data.artwork_info, artwork_data.artwork_image, count)

    def get_audit_count(self, artwork_info: ArtworkInfo) -> AuditCount:
        return self.service.get_audit_count(artwork_info)

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
        if audit_info.connection_id == 0 or audit_info.site == '':
            audit_info.connection_id = artwork_info.artwork_id
            audit_info.site = artwork_info.site
            self.service.contribute(artwork_info)
        if info_type == "status":
            audit_info.status = AuditStatus(data)
        elif info_type == "type":
            audit_info.type = AuditType(data)
            if d_reason is not None:
                audit_info.reason = str(d_reason)
        self.apply_update(audit_info)
