from typing import Iterable

import httpx

from model.artwork import ArtworkImage
from sites.mihoyobbs.base import CreateArtworkInfoFromAPIResponse, CreateArtworkListFromAPIResponse, \
    MArtworkInfo


def get_list_uri() -> str:
    return f"https://bbs-api.mihoyo.com/post/wapi/getForumPostList"


def get_info_url(post_id: int) -> str:
    return f"https://bbs-api.mihoyo.com/post/wapi/getPostFull?gids=2&post_id={post_id}&read=1"


def get_list_url_params(forum_id: int, is_good: bool = False, is_hot: bool = False, page_size: int = 20) -> dict:
    # forum_id=29&gids=2&is_good=false&is_hot=false&page_size=20&sort_type=1
    params = {
        "forum_id": forum_id,
        "gids": 2,
        "is_good": is_good,
        "is_hot": is_hot,
        "page_size": page_size,
        "sort_type": 1
    }
    return params


class MihoyobbsApi:
    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.72 Safari/537.36",
            "Referer": "https://bbs.mihoyo.com/"
        }

    def get_images_params(self, resize: int = 600, quality: int = 80, auto_orient: int = 0, interlace: int = 1,
                          images_format: str = "jpg"):
        """
        image/resize,s_600/quality,q_80/auto-orient,0/interlace,1/format,jpg
        :param resize: 图片大小
        :param quality: 图片质量
        :param auto_orient: 自适应
        :param interlace: 未知
        :param images_format: 图片格式
        :return:
        """
        params = f"image/resize,s_{resize}/quality,q_{quality}/auto-orient," \
                 f"{auto_orient}/interlace,{interlace}/format,{images_format}"
        return {
            "x-oss-process": params
        }

    def get_artwork_list(self, forum_id: int, is_good: bool = False, is_hot: bool = False, page_size: int = 20):
        url = get_list_uri()
        headers = self.get_headers()
        params = get_list_url_params(forum_id=forum_id, is_good=is_good, is_hot=is_hot, page_size=page_size)
        response = httpx.get(url=url, headers=headers, params=params)
        if response.is_error:
            return None
        return CreateArtworkListFromAPIResponse(response.json())

    def get_artwork_info(self, post_id: int) -> MArtworkInfo:
        url = get_info_url(post_id)
        headers = self.get_headers()
        response = httpx.get(url=url, headers=headers)
        if response.is_error:
            return None
        return CreateArtworkInfoFromAPIResponse(response.json())

    def get_images_by_artid(self, post_id: int) -> Iterable[ArtworkImage]:
        artwork_info = self.get_artwork_info(post_id)
        if artwork_info is None:
            return None
        art_list = []
        for url in artwork_info.image_list:
            headers = self.get_headers()
            params = self.get_images_params()
            response = httpx.get(url=url, headers=headers, params=params)
            if response.is_error:
                return None
            art_list.append(ArtworkImage(artwork_info.post_id, data=response.content))
        return art_list
