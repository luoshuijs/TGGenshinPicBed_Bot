from src.production.service.service import BaseService, AuditService
from src.production.sites.mihoyobbs.service import MihoyobbsService
from src.production.sites.twitter.service import TwitterService
from src.production.sites.pixiv.service import PixivService


class Service(BaseService):
    def __init__(self, sql_config: dict = None):
        self.twitter = TwitterService(sql_config)
        self.mihoyobbs = MihoyobbsService(sql_config)
        self.pixiv = PixivService(sql_config)
        self.audit = AuditService(self.twitter, self.mihoyobbs, self.pixiv)
        super().__init__(self.twitter, self.mihoyobbs)


class StartService(Service):

    def __init__(self, sql_config: dict = None):
        super().__init__(sql_config)
