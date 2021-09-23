from typing import Optional


class PArtworkInfo:

    def __init__(self, database_id: int = 0, art_id: int = 0, title: str = "", tags: list = [], view_count: int = 0,
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


def CreateArtworkInfoFromAPIResponse(response: dict) -> Optional[PArtworkInfo]:
    if response["error"]:
        return None
    try:
        details = response["body"]["illust_details"]
    except (AttributeError, TypeError):
        return None
    return PArtworkInfo(art_id=details["id"], title=details["title"], tags=details["tags"],
                        view_count=details["rating_view"], like_count=details["rating_count"],
                        love_count=details["bookmark_user_total"], author_id=details["user_id"],
                        upload_timestamp=details["upload_timestamp"]
                        )


def CreateArtworkFromSQLData(data: tuple) -> PArtworkInfo:
    (database_id, art_id, title, tags, view_count, like_count,
     love_count, author_id, upload_timestamp) = data
    data = PArtworkInfo(database_id, art_id, title=title, view_count=view_count, like_count=like_count,
                        love_count=love_count, author_id=author_id, upload_timestamp=upload_timestamp)
    data.SetStringTags(tags)
    return data

