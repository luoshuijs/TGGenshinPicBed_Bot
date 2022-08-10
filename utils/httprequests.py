import httpx
import asyncio
import ujson
import time
from logger import Log


class Rsp:
    def __init__(self, status=True, message=None, data=None):
        self.data = data
        self.status = status
        self.message = message


class HttpRequests(object):

    def __init__(self, proxies=None):
        self.client = httpx.AsyncClient(proxies=proxies)

    async def aclose(self):
        await self.client.aclose()

    def Request(self, method, url, headers=None, data=None, params=None) -> Rsp:
        i = 0
        while True:
            i += 1
            try:
                if method == "GET":
                    data = httpx.get(url, headers=headers, params=params)
                elif method == "POST":
                    data = httpx.post(url, headers=headers, data=data)
            except BaseException as TError:
                Log.warning("Url: %s 请求错误" % url)
                if i >= 3:
                    Rsp.code = 3
                    Rsp.message = TError
                    break
            else:
                if data.status_code == 200:
                    Rsp.code = 0
                elif data.status_code == 403:
                    if i >= 3:
                        Rsp.code = 2
                        Rsp.message = "403频繁"
                        break
                    Log.warning("Url: %s 请求错误" % url)
                    Log.warning("403频繁,休眠240s")
                    time.sleep(240)
                elif data.status_code == 404:
                    Rsp.code = 2
                    Rsp.message = "404无效地址"
                    break
                elif data.status_code == 405:
                    Rsp.code = 2
                    Rsp.message = "请求方法错误"
                    break
                else:
                    Log.warning("Url: %s 请求错误" % url)
                    Log.warning("status_code: %s " % data.status_code)
                    Rsp.code = 1
                Rsp.data = data.text
                break
        return Rsp

    def Request_json(self, method, url, headers=None, data=None, params=None):
        try:
            Rsp.data = ujson.loads(Rsp.data)
        except BaseException as TError:
            Rsp.code = 2
            Rsp.message = "解析JSON失败"
        return Rsp

    async def ARequest(self, method, url, headers=None, data=None, params=None) -> Rsp:
        if headers is not None:
            headers = httpx.Headers(headers)
        i = 0
        while True:
            i += 1
            try:
                if method == "GET":
                    data = await self.client.get(url, headers=headers, params=params)
                elif method == "POST":
                    data = await self.client.post(url, headers=headers, data=data)
            except BaseException as TError:
                Log.warning("Url: %s 请求错误" % url)
                if i >= 3:
                    Rsp.code = 3
                    Rsp.message = TError
                    break
            else:
                if data.status_code == 200:
                    Rsp.code = 0
                elif data.status_code == 403:
                    if i >= 3:
                        Rsp.code = 2
                        Rsp.message = "403频繁"
                        break
                    Log.warning("Url: %s 请求错误" % url)
                    Log.warning("403频繁,休眠240s")
                    await asyncio.sleep(240)
                elif data.status_code == 404:
                    Rsp.code = 2
                    Rsp.message = "404无效地址"
                    break
                elif data.status_code == 500:
                    Log.warning("撞墙，等待60S")
                    await asyncio.sleep(60)
                    continue
                else:
                    Log.warning("Url: %s 请求错误" % url)
                    Log.warning("status_code: %s " % data.status_code)
                    Rsp.code = 1
                Rsp.data = data.text
                break
        return Rsp

    async def ARequest_json(self, method, url, headers=None, data=None, params=None):
        i = 0
        while True:
            i += 1
            Rsp = await self.ARequest(method, url, headers, data, params)
            if Rsp.code < 1:
                try:
                    Rsp.data = ujson.loads(Rsp.data)
                except BaseException as TError:
                    Rsp.code = 2
                    Rsp.message = "解析JSON失败"
            return Rsp
