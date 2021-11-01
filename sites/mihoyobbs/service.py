from typing import Tuple, Iterable, Optional

from model.artwork import ArtworkInfo, ArtworkImage
from model.containers import ArtworkData
from sites import listener
from sites.mihoyobbs.api import MihoyobbsApi
from sites.mihoyobbs.repository import MihoyobbsRepository


@listener(site_name="mihoyobbs", module_name="MihoyobbsService")
class MihoyobbsService:
    def __init__(self, sql_config=None, **args):
        self.repository = MihoyobbsRepository(**sql_config)
        self.api = MihoyobbsApi()

    def get_artwork_info_and_image(self, post_id: int) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        temp_artwork_info = self.MihoyobbsDownloader.MihoyobbsApi.get_artwork_info(post_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.api.get_images_by_artid(post_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        return artwork_info, artwork_image

    def contribute_start(self, post_id: int) -> ArtworkData:
        artwork_data = ArtworkData()
        temp_artwork_info = self.repository.get_art_by_artid(post_id)
        if temp_artwork_info is not None:
            artwork_data.SetError("已经存在数据库")
            return artwork_data
        temp_artwork_info = self.api.get_artwork_info(post_id)
        if temp_artwork_info is None:
            artwork_data.SetError("已经存在数据库")
            return artwork_data
        artwork_image = self.api.get_images_by_artid(post_id)
        artwork_info = temp_artwork_info.GetArtworkInfo()
        artwork_data.artwork_image = artwork_image
        artwork_data.artwork_info = artwork_info
        return artwork_data

    def contribute(self, artwork_info: ArtworkInfo):
        self.repository.save_art_one(artwork_info.info)
