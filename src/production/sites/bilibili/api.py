import httpx

from src.production.sites.bilibili.base import CreateArtworkInfoFromAPIResponse, BArtworkInfo


def get_info_url(dynamic_id: int) -> str:
    return f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id=={dynamic_id}"


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.72 Safari/537.36",
    }


class BilibiliApi:

    def get_artwork_info(self, dynamic_id: int) -> BArtworkInfo:
        url = get_info_url(dynamic_id)
        headers = get_headers()
        response = httpx.get(url=url, headers=headers).json()
        return CreateArtworkInfoFromAPIResponse(response)
