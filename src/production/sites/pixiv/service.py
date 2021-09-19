from typing import Tuple, Iterable, Optional

from src.base.model.newartwork import ArtworkInfo, ArtworkImage
from src.production.sites.pixiv.api import PixivApi
from src.production.sites.pixiv.repository import PixivRepository


class PixivService:
    def __init__(self, sql_config=None):
        self.PixivRepository = PixivRepository(**sql_config)
        self.PixivApi = PixivApi()

    def contribute_start(self, art_id: int) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        temp_artwork_info = self.PixivRepository.get_art_by_artid(art_id)
        if temp_artwork_info is not None:
            return None
        temp_artwork_info = self.PixivApi.get_artwork_info(art_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.PixivApi.get_images_by_artid(art_id)
        artwork_info = ArtworkInfo(data=temp_artwork_info)
        return artwork_info, artwork_image

    def contribute_confirm(self, artwork_info: ArtworkInfo):
        self.PixivRepository.save_art_one(artwork_info.info)

    def get_art_for_audit(self, audit_type: int = 1):
        art_list = self.PixivRepository.get_art_for_audit()
        art_info_list = []
        for art_id in art_list:
            info = self.PixivRepository.get_art_by_artid(art_id)
            if info is not None:
                art_info_list.append(info)
        return art_info_list


