from typing import Tuple, Iterable, Optional, List

from src.base.model.artwork import ArtworkInfo, ArtworkImage, AuditType
from src.production.sites.pixiv.api import PixivApi
from src.production.sites.pixiv.repository import PixivRepository


class PixivService:
    def __init__(self, sql_config=None):
        self.PixivRepository = PixivRepository(**sql_config)
        self.PixivApi = PixivApi()

    def get_info_and_image(self, art_id: int) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        temp_artwork_info = self.PixivApi.get_artwork_info(art_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.PixivApi.get_images_by_artid(art_id)
        artwork_info = ArtworkInfo(data=temp_artwork_info)
        return artwork_info, artwork_image

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

    def get_art_for_audit(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        art_list = self.PixivRepository.get_art_for_audit()
        art_info_list = []
        for art_info in art_list:
            info = self.PixivRepository.get_art_by_artid(art_info.connection_id)
            if info is not None:
                temp_audit_type = AuditType.SFW
                if art_info.type.value is None:
                    if info.tags.count("R-18") >= 1:
                        temp_audit_type = AuditType.R18
                else:
                    temp_audit_type = art_info.type
                if temp_audit_type == audit_type:
                    art_info_list.append(ArtworkInfo(info))
        return art_info_list

    def get_art_for_push(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        art_list = self.PixivRepository.get_art_for_push(audit_type)
        art_info_list = []
        for art_info in art_list:
            info = self.PixivRepository.get_art_by_artid(art_info.connection_id)
            art_info_list.append(ArtworkInfo(info))
        return art_info_list
