from typing import Iterable, Set, Callable, Any

from src.model.artwork import ArtworkInfo

"""
    解析返回结果
    Parse the return result
"""


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
    if not data.get("body"):
        return None
    if data.get("error"):
        return None
    illusts = data["body"]["illusts"]
    return illusts.keys()
