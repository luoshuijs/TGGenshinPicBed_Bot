import httpx
from typing import Iterable

from src.base.model.artwork import ArtworkImage
from src.production.sites.twitter.base import CreateArtworkInfoFromAPIResponse, TArtworkInfo


class TwitterApi:
    def __init__(self, cookie: str = ""):
        self.cookie = cookie

    def get_api_uri(self, tid: int):
        return f"https://cdn.syndication.twimg.com/tweet?id={tid}"

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.72 Safari/537.36",
        }

    def get_artwork_info(self, tid: int) -> TArtworkInfo:
        url = self.get_api_uri(tid)
        headers = self.get_headers()
        response = httpx.get(url=url, headers=headers).json()
        return CreateArtworkInfoFromAPIResponse(response)


class TwitterDownloader:
    def __init__(self):
        self.TwitterApi = TwitterApi()

    def get_images_by_artid(self, tid: int) -> Iterable[ArtworkImage]:
        artwork_info = self.TwitterApi.get_artwork_info(tid)
        if artwork_info is None:
            return None
        art_list = []
        for url in artwork_info.urls:
            headers = self.TwitterApi.get_headers()
            response = httpx.get(url=url, headers=headers)
            if response.is_error:
                return None
            art_list.append(ArtworkImage(artwork_info.tid, data=response.content))
        return art_list
