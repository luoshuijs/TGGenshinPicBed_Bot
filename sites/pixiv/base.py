from model.artwork import ArtworkInfo


class PixivResponse:
    def __init__(self, response=None, error_message: str = ""):
        if response is None:
            self.error: bool = True
            self.message: str = error_message
            return
        self.response: dict = response
        self.error: bool = response["error"]
        self.message: str = response["message"]
        if self.error:
            return
        try:
            self._details = response["body"]["illust_details"]
        except (AttributeError, TypeError):
            return
        self.id = self._details["id"]
        self.user_id = self._details["user_id"]
        self.upload_timestamp = self._details["upload_timestamp"]
        self.results = PArtworkInfo(art_id=self._details["id"], title=self._details["title"],
                                    tags=self._details["tags"],
                                    view_count=self._details["rating_view"], like_count=self._details["rating_count"],
                                    love_count=self._details["bookmark_user_total"], author_id=self._details["user_id"],
                                    upload_timestamp=self._details["upload_timestamp"]
                                    )
        self.type = int(self._details["type"])
        self.page_count = int(self._details["page_count"])
        self.urls = self.get_urls()

    def __bool__(self):
        return self.error

    def __len__(self):
        return len(self.urls)

    def get_frames_info(self) -> list:
        if self.error:
            return []
        if self.type == 2:
            return self._details["ugoira_meta"]["frames"]

    def get_urls(self, quality: int = 1) -> list:
        url: list = []
        if self.error:
            return url
        if self.type == 2:  # 类型为动图
            ugoira_meta = self._details["ugoira_meta"]
            if ugoira_meta is not None:
                url.append(ugoira_meta["src"])
                return url
        if self.page_count == 1:
            if quality == 1:
                url.append(self._details["url"])
            elif quality == 2:
                url.append(self._details["url_big"])
            elif quality == 0:
                url.append(self._details["url_s"])
        elif self.page_count >= 2:  # 多张图片存在 ugoira_meta
            manga_a = self._details["manga_a"]
            for manga in manga_a:
                if quality == 1:
                    url.append(manga["url"])
                elif quality == 2:
                    url.append(manga["url_big"])
                elif quality == 0:
                    url.append(manga["url_small"])
                else:
                    return url
        return url


class BasicPixiv:
    def __init__(self, art_id: int = 0, title: str = "", tags: list = [], view_count: int = 0,
                 like_count: int = 0, love_count: int = 0, author_id: int = 0, upload_timestamp: int = 0):
        self.art_id = art_id
        self.title = title
        self.tags = tags
        self.view_count = view_count
        self.like_count = like_count
        self.love_count = love_count
        self.author_id = author_id
        self.upload_timestamp = upload_timestamp


class PArtworkInfo:

    def __init__(self, database_id: int = 0, art_id: int = 0, title: str = "", tags: list = None, view_count: int = 0,
                 like_count: int = 0, love_count: int = 0, author_id: int = 0, upload_timestamp: int = 0):
        self.database_id = database_id
        self.art_id = art_id
        self.title = title
        self.tags = tags
        self.view_count = view_count
        self.like_count = like_count
        self.love_count = love_count
        self.author_id = author_id
        self.upload_timestamp = upload_timestamp

    def GetStringTags(self) -> str:
        tags_str: str = ""
        if len(self.tags) == 0:
            return ""
        for tag in self.tags:
            temp_tag = "#%s" % tag
            tags_str += temp_tag
        return tags_str

    def SetStringTags(self, tags: str):
        tags_list = tags.split("#")
        tags_list.remove("")
        self.tags = tags_list

    def GetArtworkInfo(self):
        artwork_info = ArtworkInfo()
        artwork_info.origin_url = f"https://www.pixiv.net/artworks/{self.art_id}"
        artwork_info.site_name = "Pixiv"
        artwork_info.site = "pixiv"
        artwork_info.info = self
        artwork_info.title = self.title
        artwork_info.tags = self.tags
        artwork_info.artwork_id = self.art_id
        artwork_info.stat.bookmark_num = self.love_count
        artwork_info.stat.like_num = self.like_count
        artwork_info.stat.view_num = self.view_count
        artwork_info.create_timestamp = self.upload_timestamp
        artwork_info.user_id = self.author_id
        return artwork_info


def CreateArtworkFromSQLData(data: tuple) -> PArtworkInfo:
    (database_id, art_id, title, tags, view_count, like_count,
     love_count, author_id, upload_timestamp) = data
    data = PArtworkInfo(database_id, art_id, title=title, view_count=view_count, like_count=like_count,
                        love_count=love_count, author_id=author_id, upload_timestamp=upload_timestamp)
    data.SetStringTags(tags)
    return data
