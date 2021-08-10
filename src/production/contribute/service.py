import re
from src.base.logger import Log
from src.base.utils.artid import ExtractArtid


class Rsp:
    def __init__(self):
        self.data = None
        self.status = True
        self.message = None


class Contribute:

    def GetIllustsID(self, data: str = "") -> Rsp:
        rsp = Rsp()
        try:
            url = data
            art_id = int(ExtractArtid(data))
            if art_id is None:
                rsp.status = False
                rsp.message = "获取失败"
                return rsp
            rsp.data = art_id
        except BaseException as err:
            Log.error(err)
            rsp.status = False
            rsp.message = "获取失败"
        return rsp
