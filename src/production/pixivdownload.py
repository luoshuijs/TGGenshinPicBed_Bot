import datetime
import secrets
import asyncio
import time
import aiomysql
from urllib import parse
from typing import Iterable
from telegram.ext import Updater
from src.base.httprequests import HttpRequests
from src.base.logger import Log
from src.model.artwork import ArtworkInfo, AuditStatus, AuditType

search_url = "https://www.pixiv.net/ajax/search/artworks/%s?word=%s&p=%s&order=date_d&mode=all&s_mode" \
             "=s_tag_full"
details_url = "https://www.pixiv.net/touch/ajax/illust/details?illust_id=%s"

comments_url = "https://www.pixiv.net/ajax/illusts/comments/roots?illust_id=%s&offset=3&limit=50&lang=zh"

recommend_url = "https://www.pixiv.net/ajax/illust/%s/recommend/init?limit=18&lang=zh"


# Forward declaration, see the end of file
def CreateArtworkInfoFromAPIResponse(data) -> ArtworkInfo:
    pass


# Forward declaration, see the end of file
class Repository:
    pass


class Pixiv:

    def __init__(self, *args, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "",
                 pixiv_cookie: str = ""):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36",
            "referer": "https://www.pixiv.net/",
            "cookie": pixiv_cookie
        }
        self.mysql_host = mysql_host
        self.mysql_port = mysql_port
        self.mysql_user = mysql_user
        self.mysql_password = mysql_password
        self.mysql_database = mysql_database
        self.client = HttpRequests()
        self.GetIllustInformationTasks = []
        self.IllustIdList = []
        self.IllustIdQueue = None
        self.illustDataList = []
        self.popularList = []
        self.recommendList = []
        self.conn = None
        self.cur = None
        self.TaskLoop = None
        self.pixiv_table = "genshin_pixiv"

    def _get_headers(self, art_id: int = None):
        if not art_id:
            art_id = ""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36",
            "Referer": f"https://www.pixiv.net/{art_id}",
            "Cookie": self.cookie,
        }

    async def download_artwork_info(self, art_id: int) -> ArtworkInfo:
        pass

    async def get_recommended_artwork(self, art_id: int) -> Iterable[int]:
        pass

    def filter_artwork(self, artwork_list: Iterable[ArtworkInfo]) -> Iterable[ArtworkInfo]:
        pass

    async def work(self, TaskLoop, sleep_time: int = 6):
        try:
            self.conn = await aiomysql.connect(host=self.mysql_host, port=self.mysql_port, user=self.mysql_user,
                                               password=self.mysql_password, db=self.mysql_database, loop=TaskLoop)
            self.cur = await self.conn.cursor()
        except Exception as err:
            Log.error("打开数据库发生错误，正在退出任务")
            Log.error(err)
            return
        while True:
            self.GetIllustInformationTasks = []
            self.IllustIdList = []
            self.IllustIdQueue = asyncio.Queue(loop=TaskLoop)
            self.illustDataList = []
            self.popularList = []
            self.recommendList = []
            Log.info("正在执行Pixiv爬虫任务")
            await self.task()
            Log.info("执行Pixiv爬虫任务完成")
            if sleep_time == -1:
                break
            elif sleep_time >= 1:
                Log.info("睡眠1小时")
                await asyncio.sleep(sleep_time)
            else:
                break
        await self.client.aclose()
        await self.cur.close()
        self.conn.close()

    async def is_logged_in(self):  # 注意，如果Cookie失效是无法爬虫，而且会一直卡住
        UserStatus_url = "https://www.pixiv.net/touch/ajax/user/self/status?lang=zh"
        UserStatus_data = await self.client.ARequest_json("GET", UserStatus_url,
                                                          headers=self.headers)
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
            remaining_count = self.IllustIdQueue.qsize()
            if remaining_count > 0 and remaining_count % 100 == 0:
                Log.info("Pixiv爬虫进度：还剩下%s张作品" % remaining_count)
            IllustIdListData = await self.IllustIdQueue.get()
            status = IllustIdListData.get("status", None)
            if status and status == "close":
                self.IllustIdQueue.put_nowait({"status": "close"})
                return
            try:
                iid = IllustIdListData["id"]
                details_data = None
                details_get_url = details_url % iid
                for tries in range(4):
                    details_req = await self.client.ARequest_json("GET", details_get_url, headers=self.headers)
                    if details_req.code != 0:
                        Log.warning("取作品信息线程%s号，作品id：%s，获取失败，正在重试" % (TaskId, iid))
                        Log.debug("取作品信息线程%s号，请求错误信息：%s" % (TaskId, details_req.message))
                        continue
                    details_data = details_req.data
                    if tries >= 3:
                        Log.error("取作品信息线程%s号，作品id：%s，获取失败，正在退出任务" % (TaskId, iid))
                    break

                if details_data is None:
                    break

                tags_data = ""
                for illust_tags in details_data["body"]["illust_details"]["tags"]:
                    if illust_tags.find("'") == -1:
                        tags_data = tags_data + "#" + illust_tags

                illust_data = dict(title=details_data["body"]["illust_details"]["title"],
                                   love=details_data["body"]["illust_details"]["bookmark_user_total"],
                                   id=details_data["body"]["illust_details"]["id"],
                                   tags=tags_data,
                                   height=details_data["body"]["illust_details"]["height"],
                                   width=details_data["body"]["illust_details"]["width"],
                                   like=details_data["body"]["illust_details"]["rating_count"],
                                   view=details_data["body"]["illust_details"]["rating_view"],
                                   user_id=details_data["body"]["illust_details"]["user_id"],
                                   upload_timestamp=details_data["body"]["illust_details"]["upload_timestamp"])
                self.illustDataList.append(illust_data)
                Log.debug("获取作品信息线程%s号，收到任务，作品id：%s，获取完成" % (TaskId, iid))
            finally:
                self.IllustIdQueue.task_done()

    async def task(self):
        if not await self.is_logged_in():
            return
        Log.info("准备开始爬虫任务")
        Log.info("正在创建爬虫线程")
        for i in range(6):
            task_main = asyncio.ensure_future(self.GetIllustInformation(i))
            self.GetIllustInformationTasks.append(task_main)

        name = "原神"

        p = 1
        total = 0
        while True:
            search_get_url = search_url % (parse.quote(name), parse.quote(name), p)
            today = str(datetime.date.today())
            SevenDaysAgo = str(datetime.date.today() + datetime.timedelta(-7))
            search_get_url += "&scd=%s&ecd=%s" % (today, SevenDaysAgo)
            search_req = await self.client.ARequest_json("GET", search_get_url, headers=self.headers)

            if search_req.code != 0:
                Log.debug(search_req.message)
                return

            permanent_list = search_req.data["body"]["popular"]["permanent"]
            recent_list = search_req.data["body"]["popular"]["recent"]
            illustManga_list = search_req.data["body"]["illustManga"]["data"]
            illustManga_total = search_req.data["body"]["illustManga"]["total"]

            for temp_list in permanent_list:
                iid = temp_list["id"]
                if not iid in self.popularList:
                    self.popularList.append(iid)

            for temp_list in recent_list:
                iid = temp_list["id"]
                if not iid in self.popularList:
                    self.popularList.append(iid)

            for illustManga_data in illustManga_list:
                if "isAdContainer" in illustManga_data:
                    continue
                try:
                    self.IllustIdQueue.put_nowait({"id": illustManga_data["id"]})
                    # self.IllustIdList.append({"id": illustManga_data["id"]})
                except BaseException as err:
                    Log.error("读取数据处理错误，错误信息如下")
                    Log.error(err)
                    Log.debug("错误数据信息如下")
                    Log.debug(illustManga_data)
                    continue
                total = total + 1
            if illustManga_total == total:
                break
            p = p + 1

        try:
            for temp_id in self.popularList:
                self.IllustIdQueue.put_nowait({"id": temp_id})
                # self.IllustIdList.append({"id": temp_id})
        except BaseException as err:
            Log.error("写入数据处理错误，错误信息如下")
            Log.error(err)

        recommend_mun = 0  # 根据人气作品寻找推荐作品
        for temp_id in self.popularList:
            recommend_get_url = recommend_url % temp_id

            search_req = await self.client.ARequest_json("GET", recommend_get_url, headers=self.headers)

            if search_req.code != 0:
                Log.debug(search_req.message)
                continue
            recommend_illusts = search_req.data["body"]["illusts"]

            for illustdata_temp in recommend_illusts:
                if "isAdContainer" in illustdata_temp:
                    continue
                if "原神" in illustdata_temp["tags"]:
                    try:
                        self.recommendList.append(illustdata_temp["id"])
                    except BaseException as err:
                        Log.error("读取数据处理错误，错误信息如下")
                        Log.error(err)
                        Log.debug("错误数据信息如下")
                        Log.debug(illustdata_temp)
                        continue
                    recommend_mun += 1

        recommend_int = 36
        for i in range(recommend_int):  # 随机选择18个作品
            temp_id = secrets.choice(self.recommendList)
            try:
                self.IllustIdQueue.put_nowait({"id": temp_id})
                # self.IllustIdList.append({"id": temp_id})
            except BaseException as err:
                Log.error("读取数据处理错误，错误信息如下")
                Log.error(err)
                continue

        Log.info(
            "7天一共有%s个普通作品，%s个热门作品，%s个推荐作品，随机选择推荐作品%s个" % (total, len(self.popularList), recommend_mun, recommend_int))

        Log.info("等待作业完成")
        await self.IllustIdQueue.join()
        self.IllustIdQueue.put_nowait({"status": "close"})
        # self.IllustIdList.append({"status": "close"})
        await asyncio.wait(self.GetIllustInformationTasks)
        Log.info("作业完成")

        self.illustDataList.sort(key=lambda i: i['love'], reverse=True)  # 排序

        sql_query_data = []
        for illust_data in self.illustDataList:
            tags = illust_data["tags"]
            RStr = "R-18"
            filterStrTemp = RStr.lower()
            TagsTemp = tags.lower()
            if TagsTemp.rfind(filterStrTemp) != -1:  # 要求提升2倍
                if illust_data["love"] < 2000:
                    continue
            correctA = (time.time() - illust_data["upload_timestamp"]) / 24 / 60 / 60 * 100
            if 10 <= correctA <= 300 and illust_data["love"] >= 700:
                if illust_data["love"] < 1000 - correctA:
                    continue
            else:
                if illust_data["love"] < 1000:
                    continue
            if illust_data["love"] < 1000:
                Log.debug(
                    "illust id %s title %s love %s" % (illust_data["id"], illust_data["title"], illust_data["love"]))
            Log.debug("作品标题：%s，作品id：%s，收藏：%s" % (illust_data["title"], illust_data["id"], illust_data["love"]))

            query_data = (int(illust_data["id"]), illust_data["title"], illust_data["tags"],
                    int(illust_data["view"]), int(illust_data["like"]), illust_data["love"],
                    int(illust_data["user_id"]), illust_data["upload_timestamp"])
            sql_query_data.append(query_data)

        query = f"""
            INSERT INTO `{self.pixiv_table}` (
                illusts_id, title, tags, view_count, like_count, love_count, user_id, upload_timestamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                tags=VALUES(tags),
                view_count=VALUES(view_count),
                like_count=VALUES(like_count),
                love_count=VALUES(love_count),
                user_id=VALUES(user_id);
        """
        try:
            Log.info("写入数据库...")
            await self.cur.executemany(query, sql_query_data)
            rowcount = self.cur.rowcount
            await self.conn.commit()
            # Log.debug("作品id：%s，获取信息成功并写入数据库" % (illust_data["id"]))
            Log.info("写入完成, rows affected=%s" % rowcount)
        except BaseException as TError:
            await self.conn.rollback()
            Log.warning("写入数据库发生错误")
            Log.error(TError)


def CreateArtworkInfoFromAPIResponse(data) -> ArtworkInfo:
    """
    Maps API json response to ArtworkInfo
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


class Repository:

    def __init__(self, sql_config = None):
        self.sql_config = sql_config
        self.sql_pool = None
        self.pixiv_table = "genshin_pixiv"
        self.pixiv_audit_table = "genshin_pixiv_audit"

    async def _get_pool(self):
        if self.sql_pool is None:
            self.sql_pool = await aiomysql.create_pool(**self.sql_config)
        return self.sql_pool

    async def _executemany(self, query, query_args):
        async with (await self._get_pool()) as conn:
            sql_cur = await conn.cursor()
            await sql_cur.executemany(query, query_args)
            rowcount = sql_cur.rowcount
            await conn.commit()
        return rowcount

    async def _execute_and_fetchall(self, query, query_args):
        async with (await self._get_pool()) as conn:
            sql_cur = await conn.cursor()
            await sql_cur.execute(query, query_args)
            result = await sql_cur.fetchall()
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

    async def save_artwork_many(self, artwork_list: Iterable[ArtworkInfo]) -> int:
        """
        Save artworks into table. Returns affected rows (not the number of inserted work)
        """
        query = f"""
            INERT INTO `{self.pixiv_table}` (
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

    Task_list = {
        pixiv.work(loop)
    }
    loop.run_until_complete(
        asyncio.wait(pixiv.work(loop))
    )

    loop.close()
