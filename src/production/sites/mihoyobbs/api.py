import httpx


def get_list_uri() -> str:
    return f"https://bbs-api.mihoyo.com/post/wapi/getForumPostList"


def get_list_url_params(is_good: bool = False, is_hot: bool = False, page_size: int = 20) -> dict:
    # forum_id=29&gids=2&is_good=false&is_hot=false&page_size=20&sort_type=1
    params = {
        "forum_id": 29,
        "gids": 2,
        "is_good": is_good,
        "is_hot": is_hot,
        "page_size": page_size,
        "sort_type": 1
    }
    return params


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.72 Safari/537.36",
    }


class MihoyonbbsApi:
    def get_artwork_list(self,is_good: bool = False, is_hot: bool = False, page_size: int = 20):
        url = get_list_uri()
        headers = get_headers()
        params = get_list_url_params(is_good=is_good,is_hot=is_hot,page_size=page_size)
        response = httpx.get(url=url, headers=headers, params=params).json()

