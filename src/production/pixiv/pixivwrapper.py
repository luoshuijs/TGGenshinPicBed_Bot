import requests
import redis
import json
import pathlib
from mysql import connector
from mysql.connector.pooling import MySQLConnectionPool
from src.production.namemap import NameMap, tag_split
from src.base.logger import Log


class Rsp:
    def __init__(self, status=True, message=None, data=None):
        self.data = data
        self.status = status
        self.message = message


class Artwork:

    def __init__(self):
        self.count = 0
        self.uri_list = []
        self.image_list = []


class ArtworkPushManager(Rsp):

    def __init__(self, pixiv=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pixiv = pixiv

    def update_status(self):
        db_id = self.data["information"]["id"]
        art_id = self.data["information"]["illusts_id"]
        self.pixiv.update_status(json.dumps([db_id, art_id]), AuditStatus.PUSHED, reason=None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            if self.pixiv and self.data:
                try:
                    self.update_status()
                except Exception as exc:
                    Log.error(exc)



class AuditType:
    SFW  = "SFW"
    NSFW = "NSFW"
    R18  = "R18"

class AuditStatus:
    INIT   = 0
    PASS   = 1
    REJECT = 2
    PUSHED = 3


class Pixiv:

    def __init__(self, mysql_host: str = "127.0.0.1", mysql_port: int = 3306, mysql_user: str = "root",
                 mysql_password: str = "", mysql_database: str = "",
                 redis_host: str = "127.0.0.1", redis_port: int = 6379,
                 redis_database: int = 0,
                 pixiv_cookie: str = "", pixiv_cache_ttl: int = 300,
                 *args, **kwargs):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.72 Safari/537.36",
            "referer": "https://www.pixiv.net/",
            "cookie": pixiv_cookie
        }
        self.pixiv_table = "genshin_pixiv"
        self.status_table = "examine"
        self.pages_url = "https://www.pixiv.net/ajax/illust/%s/pages?lang=zh"
        self.diff_queue = "tgbot:diffqueue"
        self.art_queue = "tgbot:sfw:artqueue"
        self.audit_art_info = "tgbot:auditartinfo"
        self.pending_queue = "tgbot:sfw:pendingqueue"
        self.push_queue = "tgbot:sfw:pushqueue"
        self.push_art_info = "tgbot:pushartinfo"
        self.image_cache = "tgbot:imagecache"
        self.image_cache_ttl = pixiv_cache_ttl

        self.name_map_file = pathlib.Path(__file__).parent.joinpath("../../../data/namemap.json").resolve()
        self.name_map = NameMap(self.name_map_file)

        self.audit_type = AuditType.SFW

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
            self.rdb = redis.Redis(host=redis_host, port=redis_port, db=redis_database)
        except Exception as err:
            Log.error("打开数据库发生错误，正在退出任务")
            Log.error(err)
            Rsp.status = False
            Rsp.message = "查询数据库发生错误"
            return
        # Log.info("打开数据库%s@%s:%s/%s成功" % (mysql_user, mysql_host, mysql_port, mysql_database))
        """
        if not self.is_logged_in():
            Log.error("验证Pixiv_Cookie失败，Cookie失效或过期")
            return
        """

    def get_connection(self):
        try:
            return self.sql_pool.get_connection()
        except connector.PoolError:
            return connector.connect(**self.sql_config)

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

    def get_v1(self) -> Rsp:
        """
        从数据库获取待审核的图片，放入redis缓存，
        """
        self.prep_audit()
        self.prep_tag_filter()

        result_list = self.get_arts_audit()
        arts_to_add = dict()
        # 1. Query db
        for e in result_list:
            db_id, art_id, title, tag_str, views, likes, loves = e
            chars = self.name_map.identify_characters(tag_str)
            char_names = self.name_map.get_multi_character_names(chars)
            tags = tag_split(self.format_tags(tuple(name for name_tuple in char_names for name in name_tuple)))
            formatted_tags = self.format_tags(tags)
            if formatted_tags == "":
                formatted_tags = self.format_tags(tag_split(tag_str))
            arts_to_add[json.dumps([db_id, art_id])] = json.dumps({
                "id": db_id,
                "illusts_id": art_id,
                "title": title,
                "tags": formatted_tags,
                "view_count": views,
                "like_count": likes,
                "love_count": loves,
            })
        # 2. Add to redis
        if len(arts_to_add) > 0:
            Log.info(f"adding {len(arts_to_add)} images to redis")
            with self.rdb.pipeline() as p:
                _ = p.sadd(self.diff_queue, *arts_to_add.keys()) \
                    .sdiffstore(self.art_queue, self.diff_queue, self.pending_queue) \
                    .delete(self.diff_queue) \
                    .hmset(self.audit_art_info, arts_to_add) \
                    .expire(self.audit_art_info, 1800) \
                    .execute()
        return Rsp()

    def format_tags(self, tags: list):
        return "#" + " #".join(tags) if len(tags) > 0 else ""

    def prep_audit(self):
        self.sync_tables()

    def prep_tag_filter(self):
        """
        解析tag代码，标注nsfw
        """
        results = None
        with self.get_connection() as cnx:
            # 1. Query db
            with cnx.cursor() as sql_cur:
                query = """
                    SELECT gp.id, gp.illusts_id, ex.gp_id
                    FROM `%s` AS gp
                    LEFT OUTER JOIN `%s` AS ex
                        ON gp.id=ex.gp_id AND gp.illusts_id=ex.gp_illusts_id
                    WHERE (gp.tags LIKE '%%r18%%' OR gp.tags LIKE '%%r-18%%')
                        AND (ex.type <> %%s OR ex.type IS NULL);
                """ % (self.pixiv_table, self.status_table)
                sql_cur.execute(query, (AuditType.R18,))
                results = sql_cur.fetchall()
            # 2. Update data
            with cnx.cursor() as sql_cur:
                query = """
                    INSERT INTO `%s` (
                        gp_id, gp_illusts_id, type, status
                    ) VALUES (
                        %%s, %%s, %%s, %%s
                    );
                """ % self.status_table
                data = [[e[0], e[1], AuditType.R18, AuditStatus.INIT] for e in results if e[2] is None]
                if len(data) > 0:
                    sql_cur.executemany(query, data)
            with cnx.cursor() as sql_cur:
                query = """
                    UPDATE `%s`
                    SET type=%%s, status=%%s
                    WHERE gp_id=%%s AND gp_illusts_id=%%s;
                """ % self.status_table
                data = [[AuditType.R18, AuditStatus.INIT, e[0], e[1]] for e in results if e[2] is not None]
                if len(data) > 0:
                    sql_cur.executemany(query, data)
            cnx.commit()
        return results

    def sync_tables(self):
        results = None
        if self.audit_type != AuditType.SFW:
            return
        with self.get_connection() as cnx:
            with cnx.cursor() as sql_cur:
                query = """
                    SELECT gp.id, gp.illusts_id
                    FROM `%s` AS gp
                    LEFT OUTER JOIN `%s` AS ex
                        ON gp.id=ex.gp_id AND gp.illusts_id=ex.gp_illusts_id
                    WHERE ex.gp_id IS NULL OR ex.type IS NULL;
                """ % (self.pixiv_table, self.status_table)
                sql_cur.execute(query)
                results = sql_cur.fetchall()
            with cnx.cursor() as sql_cur:
                query = """
                    INSERT INTO `%s` (
                        gp_id, gp_illusts_id, type, status
                    ) VALUES (
                        %%s, %%s, %%s, %%s
                    ) ON DUPLICATE KEY UPDATE type=VALUES(type);
                """ % self.status_table
                if results and len(results) > 0:
                    data = [[e[0], e[1], self.audit_type, AuditStatus.INIT] for e in results]
                    sql_cur.executemany(query, data)
            cnx.commit()

    def get_arts_audit(self):
        """
        从数据库获取未审核的图片
        """
        results = None
        with self.get_connection() as cnx:
            with cnx.cursor() as sql_cur:
                query = """
                    SELECT a.id, a.illusts_id, a.title, a.tags, a.view_count, a.like_count, a.love_count
                    FROM `%s` AS a
                        INNER JOIN `%s` AS b
                        ON a.id=b.gp_id AND a.illusts_id=b.gp_illusts_id
                    WHERE b.type=%%s AND b.status=%%s;
                """ % (self.pixiv_table, self.status_table)
                sql_cur.execute(query, (self.audit_type, AuditStatus.INIT))
                results = sql_cur.fetchall()
            cnx.commit()
        return results

    def next_v1(self, uri_only=False) -> Rsp:
        # 1. Query redis (transaction for atomicity)
        def update_queues(pipe):
            art_key = pipe.srandmember(self.art_queue)
            art = None
            if art_key is not None:
                art = pipe.hget(self.audit_art_info, art_key)
            pipe.multi()
            if art_key is not None:
                pipe.srem(self.art_queue, art_key)
                pipe.sadd(self.pending_queue, art_key)
            return art
        result = self.rdb.transaction(update_queues, self.art_queue, self.audit_art_info, value_from_callable=True)
        if result is None:
            return Rsp(message="无数据", data={"is_end":True})
        art_info = json.loads(result)
        db_id = art_info["id"]
        art_id = art_info["illusts_id"]
        # 2. Request image
        img_uri_list = self.get_image_uri(art_id)
        img_data = None
        if not uri_only:
            artwork = self.get_image(art_id, uri_list=img_uri_list)
        data = {
            "id": db_id,
            "img_id": art_id,
            "img_key": json.dumps([db_id, art_id]),
            "img_info": art_info,
            "img": artwork,
            "is_end": False,
        }
        return Rsp(data=data)

    def putback_v1(self, image_key: str):
        def update_queues(pipe):
            exists = pipe.sismember(self.pending_queue, image_key)
            pipe.multi()
            if exists == 1:
                pipe.srem(self.pending_queue, image_key)
                pipe.sadd(self.art_queue, image_key)
            return exists
        try:
            db_id, art_id = json.loads(image_key)
            result = self.rdb.transaction(update_queues, self.pending_queue, value_from_callable=True)
        except Exception as TError:
            Log.error("putback error %s" % image_key)
            Log.error(TError)

    def get_image(self, art_id, uri_list=None):
        artwork = Artwork()
        if not uri_list:
            uri_list = self.get_image_uri(art_id)
        count = len(uri_list)
        for art_index, uri in enumerate(uri_list):
            img_id = json.dumps([art_id, art_index])
            key = f"{self.image_cache}:{img_id}"
            raw_img = self.rdb.get(key)
            if not raw_img:
                TempHeaders = self.headers.copy()
                TempHeaders["Referer"] = "https://www.pixiv.net/artworks/%s" % art_id
                res = requests.get(uri, headers=TempHeaders, timeout=20)
                raw_img = res.content
                _ = self.rdb.setex(key, self.image_cache_ttl, raw_img)
            artwork.uri_list.append(uri)
            artwork.image_list.append(raw_img)
            artwork.count += 1
        return artwork

    def get_image_uri(self, art_id):
        TempHeaders = self.headers.copy()
        TempHeaders["Referer"] = "https://www.pixiv.net/artworks/%s" % art_id
        illust_pages = requests.get(self.pages_url % art_id, headers=TempHeaders).json()
        img_urls = [img_info["urls"]["regular"] for img_info in illust_pages["body"]]
        return img_urls

    def ifpsss_v1(self, result: bool = False, reason: str = "", img_key: str = None) -> Rsp:
        status = AuditStatus.REJECT
        if result:
            status = AuditStatus.PASS
            reason = None
        rsp = Rsp()
        try:
            self.update_status(img_key, status, reason)
        except Exception as TError:
            Log.error("更新数据库发生错误")
            Log.error(TError)
            rsp.status = False
            rsp.message = "更新数据库发生错误"
        return rsp

    def update_status(self, img_key: str, status: int, reason: str = None):
        img = json.loads(img_key)
        db_id, art_id = img
        query = """
            UPDATE `%s`
            SET %s `status`=%%s, `reason`=%%s
            WHERE gp_id=%%s and gp_illusts_id=%%s;
        """
        query_patch = ""
        data = (status, reason, db_id, art_id)
        if (reason == "R18" or reason == "NSFW") and self.audit_type == AuditType.SFW:
            t = AuditType.R18 if reason == "R18" else AuditType.NSFW
            data = (t, AuditStatus.INIT, reason, db_id, art_id)
            query_patch = "`type`=%s,"
        query = query % (self.status_table, query_patch)
        with self.get_connection() as cnx:
            with cnx.cursor() as sql_cur:
                self.rdb.srem(self.pending_queue, img_key)
                sql_cur.execute(query, data)
            cnx.commit()

    def get_arts_push(self, audit_type: str = "", audit_status: str = AuditStatus.PASS):
        with self.get_connection() as cnx:
            with cnx.cursor() as sql_cur:
                query = """
                    SELECT a.id, a.illusts_id, a.title, a.tags, a.view_count, a.like_count,
                           a.love_count, a.user_id, a.upload_timestamp, b.type
                    FROM `%s` AS a
                        INNER JOIN `%s` AS b
                        ON a.id=b.gp_id AND a.illusts_id=b.gp_illusts_id
                    WHERE b.type=%%s AND b.status=%%s;
                """ % (self.pixiv_table, self.status_table)
                sql_cur.execute(query, (audit_type, audit_status))
                results = sql_cur.fetchall()
            cnx.commit()
        return results

    def push_v1(self) -> Rsp:
        result_list = self.get_arts_push(self.audit_type, AuditStatus.PASS)
        img_dict = {}
        for e in result_list:
            # 1. Parse art info
            db_id = e[0]
            art_id = e[1]
            tag_str = e[3]
            chars = self.name_map.identify_characters(tag_str)
            char_names = self.name_map.get_multi_character_names(chars)
            tags = ""
            if len(char_names) > 0:
                tags = "#" + "#".join(tuple(name for name_tuple in char_names for name in name_tuple))
            img_data = {
                "id": db_id,
                "illusts_id": art_id,
                "title": e[2],
                "tags": tags,
                "view_count": e[4],
                "like_count": e[5],
                "love_count": e[6],
                "user_id": e[7],
                "upload_timestamp": e[8],
                "audit_Type": e[9],
            }
            tags = tag_split(img_data["tags"])
            formatted_tags = "#" + " #".join(tags) if len(tags) > 0 else ""
            img_data["tags"] = formatted_tags
            # 2. Format key, value
            img_info = json.dumps(img_data)
            img_key = json.dumps([db_id, art_id])
            # 3. Push to redis
            img_dict[img_key] = img_info
        count = 0
        if len(img_dict) > 0:
            with self.rdb.pipeline() as p:
                results = p.sadd(self.push_queue, *img_dict.keys()) \
                    .hmset(self.push_art_info, img_dict) \
                    .expire(self.push_queue, 300) \
                    .expire(self.push_art_info, 330) \
                    .execute()
            count, _, _, _ = results
        rsp = Rsp()
        rsp.data = {
            "count": count,
        }
        return rsp

    def normalize_tags(self, tags_str: str):
        tags = tags_str.split("#")
        tags = [s.strip() for s in tags if len(s) > 0]
        return tags

    def nextpush_v1(self) -> ArtworkPushManager:
        # 1. Query redis
        results = img_key = img_info = None
        with self.rdb.pipeline() as p:
            results = p.spop(self.push_queue) \
                    .scard(self.push_queue) \
                    .execute()
            img_key, count = results
        if img_key is None:
            return ArtworkPushManager(status=False, message="推送完成")
        with self.rdb.pipeline() as p:
            results = p.hget(self.push_art_info, img_key) \
                    .execute()
            img_info, = results # keep the comma. results is an iterative object
        if img_info is None:
            Log.error("art %s not found in redis" % img_key)
            return ArtworkPushManager(status=False, message="推送完成")
        img_info = json.loads(img_info)
        db_id = img_info["id"]
        art_id = img_info["illusts_id"]
        # 2. Request image
        artwork = self.get_image(art_id)
        data = {
            "information": img_info,
            "img": artwork,
            "remaining": count,
        }
        return ArtworkPushManager(data=data, pixiv=self)

    def exit(self) -> Rsp:
        return Rsp()


class PixivNSFW(Pixiv):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.art_queue = "tgbot:nsfw:artqueue"
        self.pending_queue = "tgbot:nsfw:pendingqueue"
        self.push_queue = "tgbot:nsfw:pushqueue"
        self.audit_type = AuditType.NSFW

    def sync_tables(self):
        pass

    def update_status(self, img_info: str, status: int, reason: str = None):
        img = json.loads(img_info)
        db_id, art_id = img
        query = """
            UPDATE `%s`
            SET %s `status`=%%s, `reason`=%%s
            WHERE gp_id=%%s and gp_illusts_id=%%s;
        """
        query_patch = ""
        data = (status, reason, db_id, art_id)
        if reason == "R18" and self.audit_type == AuditType.NSFW:
            t = AuditType.R18
            data = (t, AuditStatus.INIT, reason, db_id, art_id)
            query_patch = "`type`=%s,"
        query = query % (self.status_table, query_patch)
        with self.get_connection() as cnx:
            with cnx.cursor() as sql_cur:
                sql_cur.execute(query, data)
            cnx.commit()
        self.rdb.srem(self.pending_queue, img_info)


class PixivR18(Pixiv):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.art_queue = "tgbot:r18:artqueue"
        self.pending_queue = "tgbot:r18:pendingqueue"
        self.push_queue = "tgbot:r18:pushqueue"
        self.audit_type = AuditType.R18

    def sync_tables(self):
        pass


class PixivWrapper:

    def __init__(self, *args, **kwargs):
        """
        Create pixiv in sfw and nsfw mode.
        """
        def get_pixiv(Cls, *args, **kwargs):
            # Cls - short for class. Used as constructor
            # Cls - 类，此处用作构造函数
            return Cls(*args, **kwargs)
        self.sfw = get_pixiv(Pixiv, *args, **kwargs)
        self.nsfw = get_pixiv(PixivNSFW, *args, **kwargs)
        self.r18 = get_pixiv(PixivR18, *args, **kwargs)

