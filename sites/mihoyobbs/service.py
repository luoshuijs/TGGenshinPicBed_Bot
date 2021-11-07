from typing import Tuple, Iterable, Optional

from model.artwork import ArtworkInfo, ArtworkImage
from model.containers import ArtworkData, parse_artwork_data
from sites import listener
from sites.mihoyobbs.api import MihoyobbsApi
from sites.mihoyobbs.repository import MihoyobbsRepository


@listener(site_name="mihoyobbs", module_name="MihoyobbsService")
class MihoyobbsService:
    def __init__(self, sql_config=None, **args):
        self.repository = MihoyobbsRepository(**sql_config)
        self.api = MihoyobbsApi()

    def get_artwork_info_and_image(self, post_id: int) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        temp_artwork_info = self.api.get_artwork_info(post_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.api.get_images_by_artid(post_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        return artwork_info, artwork_image

    def contribute_start(self, post_id: int) -> ArtworkData:
        temp_artwork_info = self.repository.get_art_by_artid(post_id)
        if temp_artwork_info is not None:
            return parse_artwork_data(error_message="已经存在数据库")
        temp_artwork_info = self.api.get_artwork_info(post_id)
        if temp_artwork_info is None:
            return parse_artwork_data(error_message="已经存在数据库")
        artwork_image = self.api.get_images_by_artid(post_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute(self, artwork_info: ArtworkInfo):
        self.repository.save_art_one(artwork_info.info)
