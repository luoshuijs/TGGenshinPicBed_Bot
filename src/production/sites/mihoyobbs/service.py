from typing import Tuple, Iterable

from src.base.model.newartwork import ArtworkInfo, ArtworkImage
from src.production.sites.mihoyobbs.api import MihoyobbsDownloader
from src.production.sites.mihoyobbs.repository import MihoyobbsRepository


class MihoyobbsService:
    def __init__(self, sql_config=None):
        self.MihoyobbsRepository = MihoyobbsRepository(**sql_config)
        self.MihoyobbsDownloader = MihoyobbsDownloader()

    def contribute_start(self, post_id: int) -> Tuple[ArtworkInfo, Iterable[ArtworkImage]]:
        temp_artwork_info = self.MihoyobbsRepository.get_art_by_artid(post_id)
        if temp_artwork_info is not None:
            return None
        temp_artwork_info = self.MihoyobbsDownloader.MihoyobbsApi.get_artwork_info(post_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.MihoyobbsDownloader.get_images_by_artid(post_id)
        artwork_info = ArtworkInfo(data=temp_artwork_info)
        return artwork_info, artwork_image

    def contribute_confirm(self, post_id: int):
        # 1. Get artwork info
        result = self.contribute_start(post_id)
        if result is None:
            return None
        artwork_info, images = result
        # 2. Save to database
        self.MihoyobbsRepository.save_art_one(artwork_info.info)