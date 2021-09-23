from src.production.service.cache import ServiceCache
from src.production.service.repository import AuditRepository
from src.production.service.service import BaseService, AuditService
from src.production.sites.mihoyobbs.service import MihoyobbsService
from src.production.sites.twitter.service import TwitterService
from src.production.sites.pixiv.service import PixivService


class Service(BaseService):
    def __init__(self, sql_config: dict = None, redis_config: dict = None, pixiv_cookie: str = ""):
        self.pixiv_cookie = pixiv_cookie
        self.twitter = TwitterService(sql_config)
        self.mihoyobbs = MihoyobbsService(sql_config)
        self.pixiv = PixivService(sql_config, self.pixiv_cookie)
        self.audit_repository = AuditRepository(**sql_config)
        self.cache = ServiceCache(**redis_config)
        self.audit = AuditService(self.twitter, self.mihoyobbs, self.pixiv,
                                  self.cache, self.audit_repository)
        super().__init__(self.twitter, self.mihoyobbs, self.pixiv, self.audit_repository)


class StartService(Service):

    def __init__(self, sql_config: dict = None, redis_config: dict = None, pixiv_cookie: str = ""):
        super().__init__(sql_config, redis_config, pixiv_cookie)
