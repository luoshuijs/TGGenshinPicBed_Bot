import httpx
import imageio
import zipfile
import os
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from logger import Log
from model.artwork import ArtworkImage
from sites.pixiv.base import PixivResponse

cur_path = os.path.realpath(os.getcwd())


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

    def get_artwork_info(self, art_id: int) -> PixivResponse:
        uri = self.get_info_uri(art_id)
        headers = self.get_headers(art_id)
        res = httpx.get(uri, headers=headers, timeout=5)
        if res.is_error:
            if res.status_code == 404:
                return PixivResponse(error_message="该作品不存在")
            else:
                return PixivResponse(error_message="请求错误")
        response = res.json()
        return PixivResponse(response)

    def get_artwork_uris(self, art_id: int) -> list:
        uri = self.get_images_uri(art_id)
        headers = self.get_headers(art_id)
        res = httpx.get(uri, headers=headers)
        if res.is_error:
            return []
        response = res.json()
        return list(img_info["urls"]["regular"] for img_info in response["body"])

    def get_images(self, response: PixivResponse) -> List[ArtworkImage]:
        art_list = []
        if response.type == 2:
            ims_list: list = []
            temp_path = os.path.join(cur_path, 'temp')  # 获取临时文件目录
            if not os.path.exists(temp_path):
                os.mkdir(temp_path)  # 如果不存在这个文件夹，就自动创建一个
            zip_file_name = os.path.join(temp_path, f"{response.id}.zip")  # 创建ZIP文件名
            gif_file_name = os.path.join(temp_path, f"{response.id}.gif")  # 创建GIF文件名
            if os.path.isfile(gif_file_name):
                with open(gif_file_name, 'rb+') as f:
                    art_list.append(ArtworkImage(response.id, data=f.read()))
                return art_list
            data = self.download_image(response.id, response.urls[0])  # 下载文件
            temp_zip_file = open(zip_file_name, mode='wb+')  # 打开文件
            temp_zip_file.write(data.data)
            zip_file = zipfile.ZipFile(file=zip_file_name)
            frames = response.get_frames_info()  # 获取图片序列文件名和图片延迟
            all_delay: int = 0
            for frame in frames:
                file_name = frame["file"]  # 获取文件名
                all_delay += frame["delay"]  # 总动画时长
                file_data = zip_file.read(file_name)
                ims_list.append(imageio.imread(uri=file_data))
            src_img_delay = (all_delay / len(frames)) / 1000  # 平均，单位为秒
            imageio.mimsave(uri=gif_file_name, ims=ims_list, format="GIF", duration=src_img_delay)
            gif_file = open(gif_file_name, mode='rb+')
            gif_data = gif_file.read()
            art_list.append(ArtworkImage(response.id, data=gif_data))
            gif_file.close()  # 关闭文件
            temp_zip_file.close()
            # os.remove(zip_file_name)  # 删除缓存文件
            # os.remove(gif_file_name)
            return art_list
        else:
            urls = response.urls
            if len(urls) == 0:
                return []
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_uri = {
                    executor.submit(self.download_image, response.id, urls[page], page)
                    : page for page in range(len(urls))
                }
                for future in as_completed(future_to_uri):
                    data: ArtworkImage = future.result()
                    art_list.append(data)

            def take_page(elem: ArtworkImage):
                return elem.page

            art_list.sort(key=take_page)
            return art_list

    def download_image(self, art_id: int, url: str, page: int = 0) -> ArtworkImage:
        headers = self.get_headers(art_id)
        response = httpx.get(url, headers=headers, timeout=5)
        if response.is_error:
            return ArtworkImage(art_id, page, True)
        return ArtworkImage(art_id, page, data=response.content)
