from typing import Iterable, Set, Callable, Any
from model.artist import ArtistCrawlInfo

"""
    解析返回结果
    Parse the return result
"""
class ArtworkInfo:

    def __init__(self, id=0, art_id=0, title="", tags="", view_count=0, like_count=0, love_count=0, author_id=0,
                 upload_timestamp=0, audit_info=None):
        self.id = id
        self.art_id = art_id
        self.title = title
        self.tags = tags
        self.view_count = view_count
        self.like_count = like_count
        self.love_count = love_count
        self.author_id = author_id
        self.upload_timestamp = upload_timestamp




class SearchResult:
    """
    解析搜素结果
    Parse the search results
    """

    def __init__(self, total: int, popular_permanent=None, popular_recent=None,
                 illust_manga=None):
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

    def __init__(self, illusts=None, next_ids=None):
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


class ArtistCrawlUpdate:
    """
    Most recent crawled art_id on an artist
    """

    def __init__(self, user_id: int, art_id: int):
        self.user_id = user_id
        self.art_id = art_id


"""
    映射数据
    Map data
"""


def CreateArtworkInfoFromAPIResponse(data: dict) -> ArtworkInfo:
    """
    把ArtworkInfoAPI的json响应映射到ArtworkInfo
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


def CreateSearchResultFromAPIResponse(data: dict) -> SearchResult:
    """
    把SearchResultAPI的json响应映射到SearchResult
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


def CreateRecommendResultFromAPIResponse(data: dict) -> RecommendResult:
    """
    把RecommendResultAPI的json响应映射到RecommendResult
    Maps pixiv recommend API json response to RecommendResult
    """
    if not data.get("body"):
        return None
    if data.get("error"):
        return None
    illusts = data["body"]["illusts"]
    next_ids = data["body"]["nextIds"]
    return RecommendResult(illusts=illusts, next_ids=next_ids)


def CreateUserAllIllustsResultFromAPIResponse(data: dict) -> Iterable[int]:
    illusts_list = []
    if not data.get("body"):
        return None
    if data.get("error"):
        return None
    illusts = data["body"]["illusts"]
    for i in illusts.keys():
        illusts_list.append(int(i))
    return illusts_list


"""
    Map SQL Query result
"""


def CreateArtistCrawlInfoFromSQLResult(data) -> Iterable[ArtistCrawlInfo]:
    if len(data) == 0:
        return []
    artists = [
        ArtistCrawlInfo(
            user_id=a[0],
            last_art_id=a[1],
            last_crawled_at=a[2],
            approved_art_count=a[3],
        )
        for a in data
    ]
    return artists
