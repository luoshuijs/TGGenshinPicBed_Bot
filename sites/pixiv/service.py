from typing import List

from model.artwork import ArtworkInfo, AuditType
from model.containers import ArtworkData
from model.helpers import parse_artwork_data
from sites import listener
from sites.pixiv.api import PixivApi
from sites.pixiv.repository import PixivRepository


def artwork_data(args):
    pass


@listener(site_name="pixiv", module_name="PixivService")
class PixivService:
    def __init__(self, sql_config: dict = None, pixiv_cookie: str = "", **args):
        self.repository = PixivRepository(**sql_config)
        self.api = PixivApi(pixiv_cookie)

    def get_artwork_info_and_image(self, artwork_id: int) -> ArtworkData:
        temp_artwork_info_response = self.api.get_artwork_info(artwork_id)
        if bool(temp_artwork_info_response):
            return parse_artwork_data(error_message=temp_artwork_info_response.message)
        artwork_image = self.api.get_images(temp_artwork_info_response)
        artwork_info = temp_artwork_info_response.results.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute(self, artwork_info: ArtworkInfo):
        self.repository.save_art_one(artwork_info.info)

    def contribute_start(self, art_id: int) -> ArtworkData:
        temp_artwork_info = self.repository.get_art_by_artid(art_id)
        if temp_artwork_info is not None:
            return parse_artwork_data(error_message="已经存在数据库")
        temp_artwork_info_response = self.api.get_artwork_info(art_id)
        if bool(temp_artwork_info_response):
            return parse_artwork_data(error_message=temp_artwork_info_response.message)
        artwork_image = self.api.get_images(temp_artwork_info_response)
        artwork_info = temp_artwork_info_response.results.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute_confirm(self, artwork_info: ArtworkInfo):
        self.repository.save_art_one(artwork_info.info)

    def get_art_for_audit(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        art_list = self.repository.get_art_for_audit()
        art_info_list = []
        for art_info in art_list:
            info = self.repository.get_art_by_artid(art_info.connection_id)
            if info is not None:
                temp_audit_type = AuditType.SFW
                if art_info.type.value is None:
                    if info.tags.count("R-18") >= 1:
                        temp_audit_type = AuditType.R18
                else:
                    temp_audit_type = art_info.type
                if temp_audit_type == audit_type:
                    art_info_list.append(info.GetArtworkInfo())
        return art_info_list

    def get_art_for_push(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        art_list = self.repository.get_art_for_push(audit_type)
        art_info_list = []
        for art_info in art_list:
            info = self.repository.get_art_by_artid(art_info.connection_id)
            art_info_list.append(info.GetArtworkInfo())
        return art_info_list
