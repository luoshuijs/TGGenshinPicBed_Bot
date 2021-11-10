from typing import Tuple, Iterable, Optional

from model.artwork import ArtworkInfo, ArtworkImage
from model.containers import ArtworkData
from model.helpers import parse_artwork_data
from sites import listener
from sites.twitter.api import TwitterApi
from sites.twitter.repository import TwitterRepository


@listener(site_name="twitter", module_name="TwitterService")
class TwitterService:
    def __init__(self, sql_config=None, **args):
        self.repository = TwitterRepository(**sql_config)
        self.api = TwitterApi()

    def get_artwork_info_and_image(self, art_id: int) -> ArtworkData:
        temp_artwork_info = self.api.get_artwork_info(art_id)
        if temp_artwork_info is None:
            return parse_artwork_data(error_message="请求错误")
        artwork_image = self.api.get_images_by_artid(art_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute_start(self, art_id: int) -> ArtworkData:
        temp_artwork_info = self.repository.get_art_by_artid(art_id)
        if temp_artwork_info is not None:
            return parse_artwork_data(error_message="已经存在数据库")
        temp_artwork_info = self.api.get_artwork_info(art_id)
        if temp_artwork_info is None:
            return parse_artwork_data(error_message="已经存在数据库")
        artwork_image = self.api.get_images_by_artid(art_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute(self, artwork_info: ArtworkInfo):
        # Save to database
        self.repository.save_art_one(artwork_info.info)
