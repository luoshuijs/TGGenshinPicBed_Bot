import time


class TArtworkInfo:
    def __init__(self, database_id: int = 0, tid: int = 0, text: str = "", tags: list = [], urls: list = [],
                 favorite_count: int = 0, height: int = 0, width: int = 0, author_id: int = 0,
                 created_at: int = 0):
        self.database_id = database_id
        self.urls = urls
        self.width = width
        self.height = height
        self.created_at = created_at
        self.favorite_count = favorite_count
        self.author_id = author_id
        self.title = text
        self.tid = tid
        self.tags = tags

    def GetStringTags(self) -> str:
        tags_str: str = ""
        if len(self.tags) == 0:
            return ""
        for tag in self.tags:  # 之前考虑过使用 string.join(seq) 但是还是算了
            temp_tag = "#%s" % tag
            tags_str += temp_tag
        return tags_str

    def SetStringTags(self, tags: str):
        tags_list = tags.split("#")
        tags_list.remove("")
        self.tags = tags_list


def CreateArtworkInfoFromAPIResponse(data: dict) -> TArtworkInfo:
    try:
        user = data["user"]
        photos = data["photos"]
        created_at = data["created_at"]
        id_str = data["id_str"]
        hashtags = data["entities"]["hashtags"]
        favorite_count = data["favorite_count"]
        text = data["text"]  # 标题
        userid_str = user["id_str"]
        height = photos[0]["height"]
        width = photos[0]["width"]
        art_id = int(id_str)
        user_id = int(userid_str)
    except (AttributeError, TypeError):
        return None
    try:
        temp_text = text.splitlines()[0]
    except (AttributeError, TypeError, ValueError):
        temp_text = text
    url_list: list = []
    tag_list: list = []
    for photo in photos:
        url_list.append(photo["url"])
    for tag in hashtags:
        tag_list.append(tag["text"])
    try:
        # "2021-08-22T08:02:26.000Z"
        created_timestamp = int(time.mktime(time.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")))
    except ValueError:
        created_timestamp = 0
    return TArtworkInfo(tid=art_id,
                        text=temp_text,
                        tags=tag_list,
                        urls=url_list,
                        favorite_count=favorite_count,
                        author_id=user_id,
                        height=height,
                        width=width,
                        created_at=created_timestamp
                        )


def CreateTArtworkFromSQLData(data) -> TArtworkInfo:
    (id, tid, text, tags, favorite_count, width,
     height, user_id, created_at) = data
    data = TArtworkInfo(database_id=id, tid=tid, text=text, favorite_count=favorite_count, author_id=user_id,
                        height=height, width=width, created_at=created_at)
    data.SetStringTags(tags)
    return data
