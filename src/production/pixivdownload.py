import re
import datetime
import secrets
import asyncio
import time
import aiomysql
from urllib import parse
from typing import Iterable, Set, Callable, Any
from telegram.ext import Updater
from src.base.httprequests import HttpRequests
from src.base.logger import Log
from src.model.artwork import ArtworkInfo, AuditStatus, AuditType


# Forward declaration, see the end of file
def CreateArtworkInfoFromAPIResponse(data) -> ArtworkInfo:
    pass


# Forward declaration, see the end of file
class Repository:
    pass


# Forward declaration, see the end of file
class SearchResult:
    pass


# Forward declaration, see the end of file
class RecommendResult:
    pass


# Core logic
class Pixiv:

    SEARCH_API = "https://www.pixiv.net/ajax/search/artworks/%s?word=%s&p=%s&order=date_d&mode=all&s_mode" \
                 "=s_tag_full"
    DETAILS_API = "https://www.pixiv.net/touch/ajax/illust/details?illust_id=%s"

    COMMENTS_API = "https://www.pixiv.net/ajax/illusts/comments/roots?illust_id=%s&offset=3&limit=50&lang=zh"

    RECOMMEND_API = "https://www.pixiv.net/ajax/illust/%s/recommend/init?limit=18&lang=zh"


    def __init__(self, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "",
                 pixiv_cookie: str = "", loop=None, *args):
        self.repository = Repository(
            sql_config = {
                "host": mysql_host,
                "port": mysql_port,
                "user": mysql_user,
                "password": mysql_password,
                "db": mysql_database,
                "loop": loop,
            },
        )
        self.cookie = pixiv_cookie
        self.client = HttpRequests()
        self.GetIllustInformationTasks = []
        self.artid_queue = None
        self.artwork_list = []
        self.pixiv_table = "genshin_pixiv"

    async def work(self, loop, sleep_time: int = 6):
        while True:
            self.GetIllustInformationTasks = []
            self.artid_queue = asyncio.Queue(loop=loop)
            self.artwork_list = []
            Log.info("正在执行Pixiv爬虫任务")
            await self.task()
            await self.repository.close()
            Log.info("执行Pixiv爬虫任务完成")
            if sleep_time == -1:
                break
            elif sleep_time >= 1:
                Log.info("睡眠1小时")
                await asyncio.sleep(sleep_time)
            else:
                break
        await self.client.aclose()

    async def is_logged_in(self):  # 注意，如果Cookie失效是无法爬虫，而且会一直卡住
        UserStatus_url = "https://www.pixiv.net/touch/ajax/user/self/status?lang=zh"
        UserStatus_data = await self.client.ARequest_json("GET", UserStatus_url,
                                                          headers=self._get_headers())
        if UserStatus_data.code != 0:
            Log.error("获取Pixiv用户状态失败")
            return False
        if not UserStatus_data.data["body"]["user_status"]["is_logged_in"]:
            Log.error("验证Pixiv_Cookie失败，Cookie失效或过期")
            return False
        else:
            Log.info("验证Pixiv_Cookie成功")
        return True

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
                artwork_info = await self.download_artwork_info(art_id)
                self.artwork_list.append(artwork_info)
                Log.debug("获取作品信息线程%s号，收到任务，作品id：%s，获取完成" % (TaskId, art_id))
            except Exception as TError:
                Log.error(TError)
            finally:
                self.artid_queue.task_done()

    async def task(self):
        if not await self.is_logged_in():
            return
        Log.info("准备开始爬虫任务")
        Log.info("正在创建爬虫线程")
        for i in range(6):
            task_main = asyncio.ensure_future(self.GetIllustInformation(i))
            self.GetIllustInformationTasks.append(task_main)

        # 1. Search artworks by keyword
        search_keyword = "原神"
        page = 1
        total = 0
        all_popular_id = set()
        while True:
            search_result = await self.search_artwork(search_keyword, page)
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
            recommend_result = await self.get_recommendation(art_id)
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
            Log.info(result)
            Log.info("写入完成, rows affected=%s" % rowcount)
        except Exception as TError:
            Log.warning("写入数据库发生错误")
            Log.error(TError)

    def _get_headers(self, art_id: int = None):
        if not art_id:
            art_id = ""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36",
            "Referer": f"https://www.pixiv.net/{art_id}",
            "Cookie": self.cookie,
        }

    def _get_search_url(self,
                        search_str: str,
                        search_page: int,
                        from_date: datetime.date = None,
                        to_date: datetime.date = None) -> str:
        s = parse.quote(search_str)
        date_range = ""
        if from_date and to_date:
            date_range = "&scd=%s&ecd=%s" % (to_date, from_date)
        return self.SEARCH_API % (s, s, search_page) + date_range

    def _get_recommend_url(self, art_id: int) -> str:
        return self.RECOMMEND_API % art_id

    def _get_details_url(self, art_id: int) -> str:
        return self.DETAILS_API % art_id

    async def search_artwork(self, keyword, page) -> SearchResult:
        today = datetime.date.today()
        seven_days_ago = datetime.date.today() + datetime.timedelta(-7)
        search_url = self._get_search_url(keyword, page, from_date=seven_days_ago, to_date=today)
        search_res = await self.client.ARequest_json("GET", search_url, headers=self._get_headers())
        if search_res.code != 0:
            return
        search_result = CreateSearchResultFromAPIResponse(search_res.data)
        return search_result

    def extract_id_from_search_result(self, search_result: SearchResult) -> Set[int]:
        res = search_result
        return set().union(
                res.get_all_popular_permanent_id(),
                res.get_all_popular_recent_id(),
                res.get_all_illust_manga_id())

    async def get_recommendation(self, art_id: int) -> RecommendResult:
        recommend_url = self.RECOMMEND_API % art_id
        recommend_res = await self.client.ARequest_json("GET", recommend_url, headers=self._get_headers())
        if recommend_res.code != 0:
            return
        recommend_result = CreateRecommendResultFromAPIResponse(recommend_res.data)
        return recommend_result

    async def download_artwork_info(self, art_id: int) -> ArtworkInfo:
        details_url = self._get_details_url(art_id)
        details_res = await self.client.ARequest_json("GET", details_url, headers=self._get_headers())
        if details_res.code != 0:
            return None
        artwork_info = CreateArtworkInfoFromAPIResponse(details_res.data)
        return artwork_info

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


def CreateArtworkInfoFromAPIResponse(data) -> ArtworkInfo:
    """
    Maps pixiv artwork info API json response to ArtworkInfo
    """
    details = data["body"].get("illust_details", None)
    if details is None:
        return None
    tags = "#" + "#".join(details["tags"]) if details["tags"] and len(details["tags"]) > 0 else ""
    return ArtworkInfo(
        art_id=details["id"],
        title=details["title"],
        tags=tags,
        view_count=details["rating_view"],
        like_count=details["rating_count"],
        love_count=details["bookmark_user_total"],
        author_id=details["user_id"],
        upload_timestamp=details["upload_timestamp"]
    )


def CreateSearchResultFromAPIResponse(data) -> SearchResult:
    """
    Maps pixiv search API json response to SearchResult
    """
    if not data.get("body"):
        return None
    if data.get("error"):
        return None
    popular_permanent = data["body"]["popular"]["permanent"]
    popular_recent = data["body"]["popular"]["recent"]
    illust_manga = data["body"]["illustManga"]["data"]
    illust_manga_total = data["body"]["illustManga"]["total"]
    return SearchResult(
        total=illust_manga_total,
        popular_permanent=popular_permanent,
        popular_recent=popular_recent,
        illust_manga=illust_manga,
    )


def CreateRecommendResultFromAPIResponse(data) -> RecommendResult:
    """
    Maps pixiv recommend API json response to RecommendResult
    """
    if not data.get("body"):
        return None
    if data.get("error"):
        return None
    illusts = data["body"]["illusts"]
    next_ids = data["body"]["nextIds"]
    return RecommendResult(illusts=illusts, next_ids=next_ids)


class SearchResult:

    def __init__(self, total: int, popular_permanent = None, popular_recent = None,
                 illust_manga = None):
        self.total = total
        self.popular_permanent = popular_permanent
        self.popular_recent = popular_recent
        self.illust_manga = illust_manga

    def get_all_popular_permanent_id(self) -> Set[int]:
        if not self.popular_permanent:
            return set()
        return set(info["id"] for info in self.popular_permanent if info.get("id"))

    def get_all_popular_recent_id(self) -> Set[int]:
        if not self.popular_recent:
            return set()
        return set(info["id"] for info in self.popular_recent if info.get("id"))

    def get_all_illust_manga_id(self) -> Set[int]:
        if not self.illust_manga:
            return set()
        return set(info["id"] for info in self.illust_manga if info.get("isAdContainer") is None)

    def get_illust_manga_count(self) -> int:
        if not self.illust_manga:
            return 0
        return len(self.illust_manga)


class RecommendResult:

    def __init__(self, illusts = None, next_ids = None):
        self.illusts = illusts
        self.next_ids = tuple(next_ids) if next_ids is not None else tuple()

    def get_all_illust_id(self, fn: Callable[[Any], bool]) -> Set[int]:
        if not self.illusts:
            return set()
        if not fn:
            fn = lambda _: True
        return set(info["id"] for info in self.illusts
                   if info.get("isAdContainer") is None
                   and fn(info))


class Repository:

    def __init__(self, sql_config = None):
        self.sql_config = sql_config
        self.sql_pool = None
        self.pixiv_table = "genshin_pixiv"
        self.pixiv_audit_table = "genshin_pixiv_audit"

    async def close(self):
        if self.sql_pool is None:
            return
        pool = self.sql_pool
        pool.close()
        self.sql_pool = None
        await pool.wait_closed()

    async def _get_pool(self):
        if self.sql_pool is None:
            self.sql_pool = await aiomysql.create_pool(**self.sql_config)
        return self.sql_pool

    async def _executemany(self, query, query_args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sql_cur = await conn.cursor()
            await sql_cur.executemany(query, query_args)
            rowcount = sql_cur.rowcount
            await sql_cur.close()
            await conn.commit()
        return rowcount

    async def _execute_and_fetchall(self, query, query_args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sql_cur = await conn.cursor()
            await sql_cur.execute(query, query_args)
            result = await sql_cur.fetchall()
            await sql_cur.close()
            await conn.commit()
        return result

    async def get_artists_with_multiple_approved_art(self, num: int) -> Iterable[int]:
        """
        Get user_id of artists with multiple approved art
        """
        query = f"""
            SELECT user_id, COUNT(user_id) AS count
            FROM {self.pixiv_audit_table}
            WHERE status=%s OR status=%s
            GROUP BY user_id
            HAVING count>%s;
        """
        query_args = (AuditStatus.PASS.value, AuditStatus.PUSH.value, num)
        return await self._execute_and_fetchall(query, query_args)

    async def save_artwork_many(self, artwork_list: Iterable[ArtworkInfo]) -> int:
        """
        Save artworks into table. Returns affected rows (not the number of inserted work)
        """
        query = f"""
            INSERT INTO `{self.pixiv_table}` (
                illusts_id, title, tags, view_count, like_count, love_count,
                user_id, upload_timestamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                tags=VALUES(tags),
                view_count=VALUES(view_count),
                like_count=VALUES(like_count),
                love_count=VALUES(love_count),
                user_id=VALUES(user_id),
                upload_timestamp=VALUES(upload_timestamp);
        """
        query_args = tuple(
            (a.art_id, a.title, a.tags, a.view_count, a.like_count,
             a.love_count, a.author_id, a.upload_timestamp)
            for a in artwork_list
        )
        return await self._executemany(query, query_args)


# 测试使用
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
    )

    loop.run_until_complete(
        pixiv.work(loop, sleep_time=-1)
    )

    loop.close()
