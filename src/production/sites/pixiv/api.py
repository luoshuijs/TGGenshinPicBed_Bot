import httpx
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.base.logger import Log
from src.base.model.artwork import ArtworkImage
from src.production.sites.pixiv.base import PArtworkInfo, CreateArtworkInfoFromAPIResponse


class PixivApi:

    def __init__(self, cookie: str = ""):
        self.cookie = cookie
        self.is_logged_in()

    def get_images_uri(self, art_id: int):
        return f"https://www.pixiv.net/ajax/illust/{art_id}/pages"

    def get_info_uri(self, art_id: int):
        return f"https://www.pixiv.net/touch/ajax/illust/details?illust_id={art_id}"

    def get_headers(self, art_id: int = 0):
        if art_id == 0:
            referer = "https://www.pixiv.net"
        else:
            referer = f"https://www.pixiv.net/artworks/{art_id}"
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.72 Safari/537.36",
            "Referer": referer,
            "Cookie": self.cookie,
        }

    def is_logged_in(self):
        user_status_url = "https://www.pixiv.net/touch/ajax/user/self/status?lang=zh"
        user_status_data = httpx.get(user_status_url, headers=self.get_headers())
        if user_status_data.is_error:
            Log.error("获取Pixiv用户状态失败")
            return False
        data = user_status_data.json()
        if not data["body"]["user_status"]["is_logged_in"]:
            Log.warning("验证Pixiv_Cookie失败：Cookie失效或过期，可能因此导致获取部分作品信息失败。")
            return False
        else:
            Log.info("验证Pixiv_Cookie成功")
        return True

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
        if urls is None:
            return None
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_uri = {executor.submit(self.download_image, art_id, url): url for url in urls}
            for future in as_completed(future_to_uri):
                data = future.result()
                art_list.append(ArtworkImage(artwork_info.art_id, data=data))
        return art_list

    def download_image(self, art_id: int, url: str) -> bytes:
        headers = self.get_headers(art_id)
        response = httpx.get(url, headers=headers, timeout=5)
        if response.is_error:
            return b""
        return response.content
