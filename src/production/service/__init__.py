from src.production.service.service import BaseService, AuditService
from src.production.sites.mihoyobbs.service import MihoyobbsService
from src.production.sites.twitter.service import TwitterService


class Service(BaseService):
    def __init__(self, sql_config: dict = None):
        self.twitter = TwitterService(sql_config)
        self.mihoyobbs = MihoyobbsService(sql_config)
        self.audit = AuditService(self.twitter, self.mihoyobbs)
        super().__init__(self.twitter, self.mihoyobbs)


class StartService(Service):

    def __init__(self, sql_config: dict = None):
        super().__init__(sql_config)
