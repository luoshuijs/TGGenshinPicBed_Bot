from typing import List

from model.artwork import ArtworkInfo, ArtworkImage, AuditType
from model.containers import ArtworkData
from model.helpers import parse_artwork_data
from sites import listener
from sites.mihoyobbs.api import MihoyobbsApi
from sites.mihoyobbs.repository import MihoyobbsRepository


@listener(site_name="mihoyobbs", module_name="MihoyobbsService")
class MihoyobbsService:
    def __init__(self, sql_config=None, **args):
        self.repository = MihoyobbsRepository(**sql_config)
        self.api = MihoyobbsApi()

    def get_artwork_info_and_image(self, post_id: int) -> ArtworkData:
        temp_artwork_info = self.api.get_artwork_info(post_id)
        if temp_artwork_info.error:
            return parse_artwork_data(error_message=temp_artwork_info.message)
        artwork_image = self.api.get_images(temp_artwork_info)
        artwork_info = temp_artwork_info.results.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute_start(self, post_id: int) -> ArtworkData:
        temp_artwork_info = self.repository.get_art_by_artid(post_id)
        if temp_artwork_info is not None:
            return parse_artwork_data(error_message="已经存在数据库")
        temp_artwork_info = self.api.get_artwork_info(post_id)
        if temp_artwork_info.error:
            return parse_artwork_data(error_message=temp_artwork_info.message)
        artwork_image = self.api.get_images(temp_artwork_info)
        artwork_info = temp_artwork_info.results.GetArtworkInfo()
        return parse_artwork_data(artwork_info, artwork_image)

    def contribute(self, artwork_info: ArtworkInfo):
        self.repository.save_art_one(artwork_info.info)

    def get_art_for_audit(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        art_list = self.repository.get_art_for_audit()
        art_info_list = []
        for art_info in art_list:
            info = self.repository.get_art_by_artid(art_info.connection_id)
            if info is not None:
                if audit_type.SFW == audit_type:
                    # 国内有啥涩涩的？
                    art_info_list.append(info.GetArtworkInfo())
        return art_info_list

    def get_art_for_push(self, audit_type: AuditType = AuditType.SFW) -> List[ArtworkInfo]:
        art_list = self.repository.get_art_for_push(audit_type)
        art_info_list = []
        for art_info in art_list:
            info = self.repository.get_art_by_artid(art_info.connection_id)
            art_info_list.append(info.GetArtworkInfo())
        return art_info_list
