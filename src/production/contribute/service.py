import re
from src.base.logger import Log


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
            if url.rfind("pixiv") != -1:  # 判断是否是pxiv域名
                matchObj = re.match(r'(.*)://www.pixiv.net/artworks/(.*)', url)
                if matchObj:
                    illusts_id = matchObj.group(2)
                    rsp.data = illusts_id
                    return rsp
                matchObj = re.match(r'(.*)://www.pixiv.net/member_illust.php?mode=medium&illust_id=(.*)', url)
                if matchObj:
                    illusts_id = matchObj.group(2)
                    rsp.data = illusts_id
                    return rsp
            elif data.isdecimal():
                rsp.data = data
                return rsp
            else:
                rsp.status = False
                rsp.message = "获取失败"
                return rsp
        except BaseException as err:
            Log.error(err)
            rsp.status = False
            rsp.message = "获取失败"
        return rsp
