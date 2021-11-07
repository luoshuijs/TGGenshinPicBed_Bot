import datetime
from typing import Iterable
from urllib import parse

from crawl.base import SearchResult, CreateSearchResultFromAPIResponse, RecommendResult, \
    CreateRecommendResultFromAPIResponse, ArtworkInfo, CreateArtworkInfoFromAPIResponse, \
    CreateUserAllIllustsResultFromAPIResponse
from utils.httprequests import HttpRequests
from logger import Log


class BasicRequest:
    SEARCH_API = "https://www.pixiv.net/ajax/search/artworks/%s?word=%s&p=%s&order=date_d&mode=all&s_mode" \
                 "=s_tag_full"
    DETAILS_API = "https://www.pixiv.net/touch/ajax/illust/details?illust_id=%s"

    COMMENTS_API = "https://www.pixiv.net/ajax/illusts/comments/roots?illust_id=%s&offset=3&limit=50&lang=zh"

    RECOMMEND_API = "https://www.pixiv.net/ajax/illust/%s/recommend/init?limit=18&lang=zh"

    USER_ALL_API = "https://www.pixiv.net/ajax/user/%s/profile/all?lang=zh"

    def __init__(self, cookie: str = ""):
        self.client = HttpRequests()
        self.cookie = cookie

    async def close(self):
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

    def _get_user_all_url(self, user_id: int) -> str:
        return self.USER_ALL_API % user_id

    async def search_artwork(self, keyword, page) -> SearchResult:
        today = datetime.date.today()
        seven_days_ago = datetime.date.today() + datetime.timedelta(-7)
        search_url = self._get_search_url(keyword, page, from_date=seven_days_ago, to_date=today)
        search_res = await self.client.ARequest_json("GET", search_url, headers=self._get_headers())
        if search_res.code != 0:
            return
        search_result = CreateSearchResultFromAPIResponse(search_res.data)
        return search_result

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

    async def get_user_all_illusts(self, user_id: int) -> Iterable[int]:
        url = self._get_user_all_url(user_id)
        res = await self.client.ARequest_json("GET", url, headers=self._get_headers())
        if res.code != 0:
            return
        return CreateUserAllIllustsResultFromAPIResponse(res.data)
