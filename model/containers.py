from typing import List

from model.artwork import ArtworkInfo, ArtworkImage, AuditInfo


class BasicData:
    def __init__(self):
        self.message: str = ""
        self.status_code: int = 1
        self.is_error: bool = False


class ArtworkData(BasicData):
    def __init__(self, artwork_info: ArtworkInfo = None, artwork_image: List[ArtworkImage] = None):
        super().__init__()
        self.artwork_info: ArtworkInfo = artwork_info
        self.artwork_image: List[ArtworkImage] = artwork_image


class ArtworkAuditData(ArtworkData):
    def __init__(self, artwork_info: ArtworkInfo = None, artwork_image: List[ArtworkImage] = None,
                 artwork_audit: AuditInfo = None):
        super().__init__(artwork_info, artwork_image)
        self.artwork_audit: AuditInfo = artwork_audit


class ArtworkPushData(ArtworkData):
    def __init__(self, artwork_info: ArtworkInfo = None, artwork_image: List[ArtworkImage] = None, count: int = 0):
        super().__init__(artwork_info, artwork_image)
        self.count = count
