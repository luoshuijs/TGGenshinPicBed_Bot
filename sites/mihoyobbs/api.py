import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import httpx

from model.artwork import ArtworkImage
from sites.mihoyobbs.base import CreateArtworkListFromAPIResponse, MiHoYoBBSResponse, ImagePostListResponse, \
    MArtworkInfo


class BaseMihoyobbsApi:
    @staticmethod
    def get_list_uri() -> str:
        return f"https://bbs-api.mihoyo.com/post/wapi/getForumPostList"

    @staticmethod
    def get_info_url(post_id: int) -> str:
        return f"https://bbs-api.mihoyo.com/post/wapi/getPostFull?gids=2&post_id={post_id}&read=1"

    @staticmethod
    def get_image_post_list_url() -> str:
        return f"https://bbs-api.mihoyo.com/post/wapi/getImagePostList"

    @staticmethod
    def get_image_post_list_params(forum_id: int, image_type: int, last_id: int = 1, gids: int = 2,
                                   page_size: int = 21) -> dict:
        """
        :param last_id: 页数
        :param forum_id: 论坛ID
        :param gids: 未知 默认为 2
        :param image_type: 类型 1为日榜 2为周榜 3为月榜
        :param page_size: 返回的图片页数
        :return:
        """
        params = {
            "forum_id": forum_id,
            "gids": gids,
            "last_id": last_id,
            "type": image_type,
            "page_size": page_size
        }
        return params

    @staticmethod
    def get_list_url_params(forum_id: int, gids: int, is_good: bool = False, is_hot: bool = False,
                            page_size: int = 20) -> dict:
        params = {
            "forum_id": forum_id,
            "gids": gids,
            "is_good": is_good,
            "is_hot": is_hot,
            "page_size": page_size,
            "sort_type": 1
        }
        return params

    @staticmethod
    def get_headers():
        """
        获取headers
        :return: 返回米忽悠BBS内置的UserAgent 和 Referer
        """
        return {
            "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; HD1910 Build/N2G47O; wv) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/68.0.3440.70 "
                          "Mobile Safari/537.36 miHoYoBBS/2.21.2",
            "Referer": "https://bbs.mihoyo.com/"
        }

    @staticmethod
    def get_images_params(resize: int = 600, quality: int = 80, auto_orient: int = 0, interlace: int = 1,
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


class AsyncMihoyobbsApi(BaseMihoyobbsApi):
    def __init__(self):
        self.client = httpx.AsyncClient(headers=self.get_headers())

    async def get_image_post_list(self, forum_id: int, image_type: int, page_size: int = 21) -> List[int]:
        url = self.get_image_post_list_url()
        post_list = []
        last_id = 1
        while True:
            params = self.get_image_post_list_params(forum_id=forum_id, image_type=image_type, page_size=page_size,
                                                     last_id=last_id)
            response = await self.client.get(url=url, params=params)
            data = ImagePostListResponse(response.json())
            if data.error:
                break
            post_list += data.post_list
            if data.is_last:
                break
            last_id = data.last_id
        return post_list

    async def get_artwork_list(self, forum_id: int, is_good: bool = False, is_hot: bool = False, page_size: int = 20):
        url = self.get_list_uri()
        params = self.get_list_url_params(forum_id=forum_id, is_good=is_good, is_hot=is_hot, page_size=page_size)
        response = await self.client.get(url=url, params=params)
        if response.is_error:
            return None
        return CreateArtworkListFromAPIResponse(response.json())

    async def get_artwork_info(self, post_id: int) -> MiHoYoBBSResponse:
        url = self.get_info_url(post_id)
        headers = self.get_headers()
        response = await self.client.get(url=url, headers=headers)
        if response.is_error:
            return MiHoYoBBSResponse(error_message="请求错误")
        return MiHoYoBBSResponse(response.json())

    async def get_images_by_artid(self, post_id: int) -> List[ArtworkImage]:
        artwork_info = await self.get_artwork_info(post_id)
        if artwork_info.error:
            return []
        urls = artwork_info.results.image_list
        art_list = []
        task_list = [
            self.download_image(artwork_info.post_id, urls[page], page) for page in range(len(urls))
        ]
        result_list = await asyncio.gather(*task_list)
        for result in result_list:
            if isinstance(result, ArtworkImage):
                art_list.append(result)

        def take_page(elem: ArtworkImage):
            return elem.page

        art_list.sort(key=take_page)
        return art_list

    async def download_image(self, art_id: int, url: str, page: int = 0) -> ArtworkImage:
        response = await self.client.get(url, params=self.get_images_params(), timeout=5)
        if response.is_error:
            return ArtworkImage(art_id, page, True)
        return ArtworkImage(art_id, page, data=response.content)

    async def close(self):
        await self.client.aclose()


class MihoyobbsApi(BaseMihoyobbsApi):

    def get_artwork_list(self, forum_id: int, is_good: bool = False, is_hot: bool = False, page_size: int = 20):
        url = self.get_list_uri()
        headers = self.get_headers()
        params = self.get_list_url_params(forum_id=forum_id, is_good=is_good, is_hot=is_hot, page_size=page_size)
        response = httpx.get(url=url, headers=headers, params=params)
        if response.is_error:
            return None
        return CreateArtworkListFromAPIResponse(response.json())

    def get_artwork_info(self, post_id: int) -> MiHoYoBBSResponse:
        url = self.get_info_url(post_id)
        headers = self.get_headers()
        response = httpx.get(url=url, headers=headers)
        if response.is_error:
            return MiHoYoBBSResponse(error_message="请求错误")
        return MiHoYoBBSResponse(response.json())

    def get_images_by_artid(self, response: MiHoYoBBSResponse) -> List[ArtworkImage]:
        if response is None:
            return []
        art_list = []
        urls = response.results.image_url_list
        if len(urls) == 0:
            return []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_uri = {
                executor.submit(self.download_image, response.results.post_id, urls[page], page)
                : page for page in range(len(urls))
            }
            for future in as_completed(future_to_uri):
                data: ArtworkImage = future.result()
                art_list.append(data)

        def take_page(elem: ArtworkImage):
            return elem.page

        art_list.sort(key=take_page)
        return art_list

    def download_image(self, post_id: int, url: str, page: int = 0) -> ArtworkImage:
        headers = self.get_headers()
        response = httpx.get(url, headers=headers, params=self.get_images_params(), timeout=5)
        if response.is_error:
            return ArtworkImage(post_id, page, True)
        return ArtworkImage(post_id, page, data=response.content)
