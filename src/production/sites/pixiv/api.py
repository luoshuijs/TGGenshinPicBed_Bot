import httpx
from typing import Optional, List

from src.base.model.artwork import ArtworkImage
from src.production.sites.pixiv.base import PArtworkInfo, CreateArtworkInfoFromAPIResponse


class PixivApi:

    def __init__(self, cookie: str = ""):
        self.cookie = cookie

    def get_images_uri(self, art_id: int):
        return f"https://www.pixiv.net/ajax/illust/{art_id}/pages"

    def get_info_uri(self, art_id: int):
        return f"https://www.pixiv.net/touch/ajax/illust/details?illust_id={art_id}"

    def get_headers(self, art_id: int):
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

    def get_artwork_uris(self, art_id: int) -> Optional[list]:
        uri = self.get_images_uri(art_id)
        headers = self.get_headers(art_id)
        res = httpx.get(uri, headers=headers)
        if res.is_error:
            return None
        response = res.json()
        return list(img_info["urls"]["regular"] for img_info in response["body"])

    def get_images_by_artid(self, art_id: int) -> Optional[List[ArtworkImage]]:
        artwork_info = self.get_artwork_info(art_id)
        if artwork_info is None:
            return None
        art_list = []
        urls = self.get_artwork_uris(art_id)
        for url in urls:
            headers = self.get_headers(art_id)
            response = httpx.get(url=url, headers=headers)
            if response.is_error:
                return None
            art_list.append(ArtworkImage(artwork_info.art_id, data=response.content))
        return art_list
