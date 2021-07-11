import re
import requests
from mysql import connector
from mysql.connector.pooling import MySQLConnectionPool
from src..logger import Log


class Rsp:
    def __init__(self):
        self.data = None
        self.status = True
        self.message = None


class Contribute:
    def __init__(self, *args, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "",
                 pixiv_cookie: str = ""
                 ):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.72 Safari/537.36",
            "referer": "https://www.pixiv.net/",
            "cookie": pixiv_cookie
        }
        self.pages_url = "https://www.pixiv.net/ajax/illust/%s/pages?lang=zh"
        self.sql_config = {
            "host": mysql_host,
            "port": mysql_port,
            "user": mysql_user,
            "password": mysql_password,
            "database": mysql_database,
        }
        try:
            self.sql_pool = MySQLConnectionPool(pool_name="",
                                                pool_size=10,
                                                pool_reset_session=False,
                                                **self.sql_config)
        except Exception as err:
            Log.error("打开数据库发生错误，正在退出任务")
            Log.error(err)
            Rsp.status = False
            Rsp.message = "查询数据库发生错误"
            return
        # Log.info("打开数据库%s@%s:%s/%s成功" % (mysql_user, mysql_host, mysql_port, mysql_database))
        if not self.is_logged_in():
            # Log.error("验证Pixiv_Cookie失败，Cookie失效或过期")
            return

    def is_logged_in(self):
        """
        获取Cookie登录状态
        """
        # 注意，如果Cookie失效是无法爬虫，而且会一直卡住。
        UserStatus_url = "https://www.pixiv.net/touch/ajax/user/self/status?lang=zh"
        try:
            UserStatus_data = requests.get(UserStatus_url, headers=self.headers.copy()).json()
            if not UserStatus_data["body"]["user_status"]["is_logged_in"]:
                return False
            else:
                return True
        except:
            pass
        return False

    def get_connection(self):
        try:
            return self.sql_pool.get_connection()
        except connector.PoolError:
            return connector.connect(**self.sql_config)

    def GetInfo(self, data) -> Rsp:
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
        except BaseException as err:
            Log.error(err)
            rsp.status = False
            rsp.message = "获取失败"
        return rsp

    def IfIllustOnline(self, illusts_id: str = "") -> Rsp:
        rsp = Rsp()
        details_url = "https://www.pixiv.net/touch/ajax/illust/details?illust_id=%s"
        GetDetails_url = details_url % (illusts_id)
        try:
            details_req = requests.get(GetDetails_url, headers=self.headers).json()  # 判断作品是否存在
            if details_req["error"]:
                rsp.status = False
                rsp.message = details_req["message"]
                return rsp
            with self.get_connection() as cnx:  # 判断作品是否存在数据库
                with cnx.cursor() as sql_cur:
                    query = """
                       SELECT * FROM genshin_pixiv WHERE illusts_id=%s
                    """ % (illusts_id)
                    sql_cur.execute(query)
                    results = sql_cur.fetchall()
                cnx.commit()
            if len(results) != 0:
                rsp.status = False
                rsp.message = "作品已经在频道发布过"
                return rsp
        except BaseException as err:
            Log.error(err)
            rsp.status = False
            rsp.message = "获取失败"
        rsp.data = details_req
        return rsp

    def PushIllust(self, DetailsData: dict) -> Rsp:
        rsp = Rsp()
        try:
            tags_data = ""
            for illust_tags in DetailsData["body"]["illust_details"]["tags"]:
                if illust_tags.find("'") == -1:
                    tags_data = tags_data + "#" + illust_tags
            query = """
                            INSERT INTO genshin_pixiv (
                            id , illusts_id, title, tags, view_count, like_count, love_count, user_id , upload_timestamp
                            ) VALUES (
                            %%s , %%s, %%s, %%s, %%s, %%s, %%s, %%s, %%s
                            )
                            """
            data = [0, DetailsData["body"]["illust_details"]["id"], DetailsData["body"]["illust_details"]["title"],
                    tags_data, int(DetailsData["body"]["illust_details"]["rating_view"]),
                    int(DetailsData["body"]["illust_details"]["rating_count"]),
                    DetailsData["body"]["illust_details"]["bookmark_user_total"],
                    int(DetailsData["body"]["illust_details"]["user_id"]),
                    DetailsData["body"]["illust_details"]["upload_timestamp"]]
            with self.get_connection() as cnx:  # 写入数据量嗷
                with cnx.cursor() as sql_cur:
                    sql_cur.execute(query, data)
                cnx.commit()
        except BaseException as err:
            Log.error(err)
            rsp.status = False
            rsp.message = "获取失败"
        return rsp
