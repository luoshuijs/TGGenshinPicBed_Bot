import httpx
from src.production.sites.twitter.base import CreateArtworkInfoFromAPIResponse


def get_api_uri(tid: int):
    return f"https://cdn.syndication.twimg.com/tweet?id={tid}"


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.72 Safari/537.36",
    }


class TwitterApi:

    def get_artwork_info(self, tid: int):
        url = get_api_uri(tid)
        headers = get_headers()
        response = httpx.get(url=url, headers=headers).json()
        return CreateArtworkInfoFromAPIResponse(response)

