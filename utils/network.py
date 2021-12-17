import asyncio
from pathlib import Path

import aiofiles
import httpx


class NetWork:
    def __init__(self, limit=30, max_connections=100, timeout=20, env=False, internal=False, proxy=None):
        """
        :param limit: keepalive connections limit
        :param max_connections: max_connections
        :param timeout:
        :param env:  debug输出:HTTPX_LOG_LEVEL=debug
        :param internal:
        :param proxy:
        """
        self.proxy = proxy
        self.internal = internal
        self.client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(timeout, connect=60),
            proxies=self.proxy,
            limits=httpx.Limits(max_keepalive_connections=limit, max_connections=max_connections),
            trust_env=env
        )

    def start(self):
        return self.client

    async def close(self):
        await asyncio.sleep(0)
        await self.client.aclose()

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc, tb):
        await asyncio.sleep(0)
        await self.client.aclose()


class ClientManager:
    def __init__(self, s, env, proxy):
        if s is None:
            self.session = NetWork(internal=True, env=env, proxy=proxy)
        else:
            self.session = s

    async def __aenter__(self):
        if isinstance(self.session, NetWork):
            return self.session.start()
        if isinstance(self.session, httpx.AsyncClient):
            return self.session

    async def __aexit__(self, exception_type, exception_value, traceback):
        if isinstance(self.session, NetWork):
            if self.session.internal:
                await self.session.close()


class AsyncRequest(object):
    def __init__(self, client=None, env=False, proxy=None, **requests_kwargs):
        self.session = client
        self.env = env
        self.proxy = proxy
        self.requests_kwargs = requests_kwargs

    async def get(self, url, headers=None, params=None):
        async with ClientManager(self.session, self.env, self.proxy) as session:
            res = await session.get(url, headers=headers, params=params)
            await asyncio.sleep(0)
            return res

    async def post(self, url, headers=None, params=None, data=None, json=None, files=None):
        async with ClientManager(self.session, self.env, self.proxy) as session:
            if json is not None:
                res = await session.post(url, headers=headers, params=params, json=json)
            elif files is not None:
                res = await session.post(url, headers=headers, params=params, files=files)
            elif data is not None:
                res = await session.post(url, headers=headers, params=params, data=data)
            else:
                res = await session.post(url, headers=headers, params=params)
            await asyncio.sleep(0)
            return res

    async def downloader(self, url='', path=None, filename=''):  # 下载器
        async with ClientManager(self.session, self.env, self.proxy) as session:
            async with session.stream("GET", url=url) as r:
                if path:
                    file = Path(path).joinpath(filename)
                else:
                    file = Path().cwd().joinpath(filename)
                async with aiofiles.open(file, 'wb') as out_file:
                    async for chunk in r.aiter_bytes():
                        await out_file.write(chunk)
                return file
