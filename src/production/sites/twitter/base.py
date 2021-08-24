import time

from src.base.utils.namemap import tag_split


class TArtworkInfo:
    def __init__(self, database_id: int = 0, art_id: int = 0, title: str = "", tags: (list, str) = None,
                 urls: list = [], favorite_count: int = 0, height: int = 0, width: int = 0, author_id: int = 0,
                 upload_timestamp: int = 0):
        self.urls = urls
        self.width = width
        self.height = height
        self.upload_timestamp = upload_timestamp
        self.favorite_count = favorite_count
        self.author_id = author_id
        self.database_id = database_id
        self.title = title
        self.art_id = art_id
        self.tags: list = []
        if type(tags) == list:
            self.tags = tags
        elif type(tags) == str:
            try:
                self.tags = list(tag_split(tags))
            except ValueError:
                self.tags = None
        else:
            self.tags = None


def CreateArtworkInfoFromAPIResponse(data: dict) -> TArtworkInfo:
    try:
        user = data["user"]
        photos = data["photos"]
        created_at = data["created_at"]
        id_str = data["id_str"]
        hashtags = data["entities"]["hashtags"]
        favorite_count = data["favorite_count"]
        text = data["text"]
    except (AttributeError, TypeError):
        return None
    url_list: list = []
    tag_list: list = []
    height = photos[0]["height"]
    width = photos[0]["width"]
    art_id = int(id_str)
    user_id = int(user)
    for photo in photos:
        url_list.append(photo["url"])
    for tag in hashtags:
        tag_list.append(tag["text"])
    try:
        # "2021-08-22T08:02:26.000Z"
        upload_timestamp = int(time.mktime(time.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")))
    except ValueError:
        upload_timestamp = 0
    return TArtworkInfo(art_id=art_id,
                        title=text,
                        tags=tag_list,
                        urls=url_list,
                        favorite_count=favorite_count,
                        author_id=user_id,
                        height=height,
                        width=width,
                        upload_timestamp=upload_timestamp
                        )
