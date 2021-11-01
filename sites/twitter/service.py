from typing import Tuple, Iterable, Optional

from model.artwork import ArtworkInfo, ArtworkImage
from model.containers import ArtworkData
from sites import listener
from sites.twitter.api import TwitterApi
from sites.twitter.repository import TwitterRepository


@listener(site_name="twitter", module_name="TwitterService")
class TwitterService:
    def __init__(self, sql_config=None, **args):
        self.repository = TwitterRepository(**sql_config)
        self.api = TwitterApi()

    def get_artwork_info_and_image(self, art_id: int) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        temp_artwork_info = self.api.get_artwork_info(art_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.api.get_images_by_artid(art_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        return artwork_info, artwork_image

    def contribute_start(self, art_id: int) -> ArtworkData:
        artwork_data = ArtworkData()
        temp_artwork_info = self.repository.get_art_by_artid(art_id)
        if temp_artwork_info is not None:
            artwork_data.SetError("已经存在数据库")
            return artwork_data
        temp_artwork_info = self.api.get_artwork_info(art_id)
        if temp_artwork_info is None:
            artwork_data.SetError("已经存在数据库")
            return artwork_data
        artwork_image = self.api.get_images_by_artid(art_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        artwork_data.artwork_image = artwork_image
        artwork_data.artwork_info = artwork_info
        return artwork_data

    def contribute(self, artwork_info: ArtworkInfo):
        # Save to database
        self.repository.save_art_one(artwork_info.info)
