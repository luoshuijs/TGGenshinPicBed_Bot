import asyncio
import unittest

from utils.network import AsyncRequest, NetWork


class TestAsyncRequest(AsyncRequest):
    def __init__(self, **requests_kwargs):
        super().__init__(**requests_kwargs)

    async def test(self, url: str):
        return await self.session.get(url)


async def MyAsyncRequestTest() -> bool:
    async with NetWork() as client:
        test_async_request = TestAsyncRequest(client=client)
        await test_async_request.test("https://github.com")
    return True


class MyTestCase(unittest.TestCase):
    def test_something(self):
        loop = asyncio.get_event_loop()
        run = [MyAsyncRequestTest()]
        loop.run_until_complete(
            asyncio.wait(run)
        )
        loop.close()
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
