import re
import secrets
import asyncio
import time
from typing import Iterable, Set
from src.base.logger import Log
from src.base.model.artwork import ArtworkInfo
from src.production.crawl.base import SearchResult
from src.production.crawl.repository import Repository
from src.production.crawl.request import BasicRequest


class Pixiv:
    def __init__(self, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "",
                 pixiv_cookie: str = "", loop=None, *args):
        self.repository = Repository(
            sql_config={
                "host": mysql_host,
                "port": mysql_port,
                "user": mysql_user,
                "password": mysql_password,
                "db": mysql_database,
                "loop": loop,
            },
        )
        self.cookie = pixiv_cookie
        self.GetIllustInformationTasks = []
        self.artid_queue = None
        self.artwork_list = []
        self.pixiv_table = "genshin_pixiv"
        self.BasicRequest = BasicRequest(cookie=self.cookie)

    async def close(self):
        await self.repository.close()
        await self.BasicRequest.close()

    async def work(self, loop, sleep_time: int = 6):
        while True:
            if not await self.BasicRequest.is_logged_in():
                return
            self.GetIllustInformationTasks = []
            self.artwork_list = []
            self.artid_queue = asyncio.Queue(loop=loop)
            Log.info("正在执行Pixiv爬虫任务")
            await self.task()
            await self.task1()
            # await self.repository.close()
            Log.info("执行Pixiv爬虫任务完成")
            if sleep_time == -1:
                break
            elif sleep_time >= 1:
                Log.info("睡眠1小时")
                await asyncio.sleep(sleep_time)
            else:
                break

    async def GetIllustInformation(self, TaskId):
        Log.info("获取作品信息线程%s号：创建完成" % TaskId)
        Log.debug("获取作品信息线程%s号：等待下载任务" % TaskId)
        while True:
            remaining_count = self.artid_queue.qsize()
            if remaining_count > 0 and remaining_count % 100 == 0:
                Log.info("Pixiv爬虫进度：还剩下%s张作品" % remaining_count)
            id_data = await self.artid_queue.get()
            if id_data.get("status") == "close":
                self.artid_queue.put_nowait({"status": "close"})
                return
            try:
                art_id = id_data["id"]
                artwork_info = await self.BasicRequest.download_artwork_info(art_id)
                self.artwork_list.append(artwork_info)
                Log.debug("获取作品信息线程%s号，收到任务，作品id：%s，获取完成" % (TaskId, art_id))
            except Exception as TError:
                Log.error(TError)
            finally:
                self.artid_queue.task_done()

    async def task(self):
        """
        获取基础爬虫数据
        爬取的数据包括7天前的数据，推荐的数据
        :return:
        """
        Log.info("准备开始基础爬虫任务")
        Log.info("正在创建爬虫线程")
        self.GetIllustInformationTasks = []
        self.artwork_list = []
        for i in range(6):
            task_main = asyncio.ensure_future(self.GetIllustInformation(i))
            self.GetIllustInformationTasks.append(task_main)

        # 1. Search artworks by keyword
        search_keyword = "原神"
        page = 1
        total = 0
        all_popular_id = set()
        while True:
            search_result = await self.BasicRequest.search_artwork(search_keyword, page)
            all_popular_id = all_popular_id.union(
                search_result.get_all_popular_permanent_id(),
                search_result.get_all_popular_recent_id())
            for art_id in search_result.get_all_illust_manga_id():
                self.artid_queue.put_nowait({"id": art_id})
            total += search_result.get_illust_manga_count()
            if total >= search_result.total:
                break
            page += 1

        for art_id in all_popular_id:
            self.artid_queue.put_nowait({"id": art_id})

        # 2. Search artwork by recommendation
        all_recommend_id = set()
        recommend_num = 0
        for art_id in all_popular_id:
            recommend_result = await self.BasicRequest.get_recommendation(art_id)
            recommend_id = recommend_result.get_all_illust_id(lambda x: "原神" in x.get("tags", ""))
            recommend_num += len(recommend_id)
            all_recommend_id = all_recommend_id.union(recommend_id)
        recommend_int = min(36, len(all_recommend_id))
        rec_tuple = tuple(all_recommend_id)
        all_recommend_id = set(secrets.choice(rec_tuple) for i in range(recommend_int))

        for art_id in all_recommend_id:
            self.artid_queue.put_nowait({"id": art_id})

        # 3. Wait for artwork details
        Log.info(
            "7天一共有%s个普通作品，%s个热门作品，%s个推荐作品，随机选择推荐作品%s个" % (
                total, len(all_recommend_id), recommend_num, recommend_int)
        )
        Log.info("等待作业完成")
        await self.artid_queue.join()
        self.artid_queue.put_nowait({"status": "close"})
        await asyncio.wait(self.GetIllustInformationTasks)
        Log.info("作业完成")

        # 4. Filter artwork based on stats
        artwork_list = sorted(self.artwork_list, key=lambda i: i.love_count, reverse=True)  # 排序
        finalized_artworks = self.filter_artwork(artwork_list)

        # 5. Write to database
        try:
            Log.info("写入数据库...")
            rowcount = await self.repository.save_artwork_many(finalized_artworks)
            Log.info("写入完成, rows affected=%s" % rowcount)
        except Exception as TError:
            Log.warning("写入数据库发生错误")
            Log.error(TError)

    async def task1(self):
        """
        获取画师推荐
        因为爬虫只获取当前前7天的数据，为了弥补没有获取以前的数据的不足
        根据画师在数据库通过的作品爬取画师以前的作品。
        :return:
        """
        Log.info("准备开始推荐爬虫任务")
        # 初始化，清空之前的数据
        self.GetIllustInformationTasks = []
        self.artwork_list = []

        for i in range(6):
            task_main = asyncio.ensure_future(self.GetIllustInformation(i))
            self.GetIllustInformationTasks.append(task_main)

        popular_artists_all = await self.repository.get_artists_with_multiple_approved_arts(num=3,
                                                                                            days_ago=7)  # 从数据库获取全部话说

        for popular_artists in popular_artists_all:
            all_illusts = await self.BasicRequest.get_user_all_illusts(popular_artists.user_id)
            if not popular_artists.last_art_id is None:
                all_illusts_f = [i for i in all_illusts if i > popular_artists.last_art_id]
            else:
                all_illusts_f = all_illusts
            for art_id in all_illusts_f:
                self.artid_queue.put_nowait({"id": art_id})
            await self.repository.save_artist_last_crawl(user_id=popular_artists.user_id,
                                                         last_art_id=max(all_illusts_f))

        self.artid_queue.put_nowait({"status": "close"})
        await asyncio.wait(self.GetIllustInformationTasks)

        if len(popular_artists_all) == 0:
            return

        finalized_artworks = self.filter_tags(self.artwork_list)

        try:
            Log.info("写入数据库...")
            rowcount = await self.repository.save_artwork_many(finalized_artworks)
            Log.info("写入完成, rows affected=%s" % rowcount)
        except Exception as TError:
            Log.warning("写入数据库发生错误")
            Log.error(TError)

    def filter_tags(self, artwork_list: Iterable[ArtworkInfo]) -> Iterable[ArtworkInfo]:
        result = []
        for artwork_info in artwork_list:
            if not "原神" in artwork_info.tags:
                continue
            if artwork_info.love_count < 300:
                continue
            result.append(artwork_info)
        return result

    def extract_id_from_search_result(self, search_result: SearchResult) -> Set[int]:
        res = search_result
        return set().union(
            res.get_all_popular_permanent_id(),
            res.get_all_popular_recent_id(),
            res.get_all_illust_manga_id())

    def filter_artwork(self, artwork_list: Iterable[ArtworkInfo]) -> Iterable[ArtworkInfo]:
        r18_regex = re.compile(r"R.?18", re.I)
        result = []
        for artwork_info in artwork_list:
            tags = artwork_info.tags
            if r18_regex.search(tags) is not None:  # 要求提升2倍
                if artwork_info.love_count < 2000:
                    continue
            days_hundred_fold = (time.time() - artwork_info.upload_timestamp) / 24 / 60 / 60 * 100
            if 10 <= days_hundred_fold <= 300 and artwork_info.love_count >= 700:
                if artwork_info.love_count < 1000 - days_hundred_fold:
                    continue
            else:
                if artwork_info.love_count < 1000:
                    continue
            result.append(artwork_info)
        return result


# 作为计划任务单独运行
# 运行命令为
# cd  //进入项目目录
# PYTHONPATH=$PYTHONPATH:   //设置python工作目录
# python3 src/production/crawl/pixivdownload.py  //执行爬虫
#
if __name__ == "__main__":
    from src.base.config import config

    loop = asyncio.get_event_loop()

    pixiv = Pixiv(
        mysql_host=config.MYSQL["host"],
        mysql_port=config.MYSQL["port"],
        mysql_user=config.MYSQL["user"],
        mysql_password=config.MYSQL["pass"],
        mysql_database=config.MYSQL["database"],
        pixiv_cookie=config.PIXIV["cookie"],
        loop=loop
    )

    run = [pixiv.work(loop, sleep_time=-1)]
    close = [pixiv.close()]

    loop.run_until_complete(
        asyncio.wait(run)
    )

    loop.run_until_complete(
        asyncio.wait(close)
    )

    loop.close()
