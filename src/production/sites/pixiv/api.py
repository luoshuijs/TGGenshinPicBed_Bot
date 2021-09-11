import httpx
from typing import Iterable
from src.production.sites.pixiv.base import PArtworkInfo, CreateArtworkInfoFromAPIResponse


class PixivApi:

    def __init__(self, cookie: str = ""):
        self.cookie = cookie

    def get_images_uri(self, art_id: int):
        return f"https://www.pixiv.net/ajax/illust/{art_id}/pages"

    def get_info_uri(self, art_id: int):
        return f"https://www.pixiv.net/touch/ajax/illust/details?illust_id={art_id}"

    def get_headers(self, art_id: str = ""):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.72 Safari/537.36",
            "Referer": f"https://www.pixiv.net/artworks/{art_id}",
            "Cookie": self.cookie,
        }

    def get_artwork_info(self, art_id: int) -> PArtworkInfo:
        uri = self.get_info_uri(art_id)
        headers = self.get_headers(art_id)
        response = httpx.get(uri, headers=headers, timeout=5).json()
        return CreateArtworkInfoFromAPIResponse(response)

    def get_artwork_uris(self, art_id: int) -> Iterable[str]:
        uri = self.get_images_uri(art_id)
        headers = self.get_headers(art_id)
        res = httpx.get(uri, headers=headers)
        response = res.json()
        return tuple(img_info["urls"]["regular"] for img_info in response["body"])


