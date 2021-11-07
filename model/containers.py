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


def parse_artwork_push_data(
        artwork_info: ArtworkInfo = None,
        artwork_image: List[ArtworkImage] = None,
        count: int = 0,
        status_code: int = 1,
        error_message: str = "") -> ArtworkPushData:
    artwork_push_data = ArtworkPushData()
    if error_message != "":
        artwork_push_data.is_error = True
        artwork_push_data.message = error_message
        if status_code == 1:
            status_code = 0
        artwork_push_data.status_code = status_code
    artwork_push_data.artwork_info = artwork_info
    artwork_push_data.artwork_info = artwork_image
    artwork_push_data.artwork_info = count
    return artwork_push_data


def parse_artwork_audit_data(
        artwork_info: ArtworkInfo = None,
        artwork_image: List[ArtworkImage] = None,
        artwork_audit: AuditInfo = None,
        status_code: int = 1,
        error_message: str = "") -> ArtworkAuditData:
    artwork_audit_data = ArtworkAuditData()
    if error_message != "":
        artwork_audit_data.is_error = True
        artwork_audit_data.message = error_message
        if status_code == 1:
            status_code = 0
        artwork_audit_data.status_code = status_code
    artwork_audit_data.artwork_info = artwork_info
    artwork_audit_data.artwork_info = artwork_image
    artwork_audit_data.artwork_audit = artwork_audit
    return artwork_audit_data


def parse_artwork_data(
        artwork_info: ArtworkInfo = None,
        artwork_image: List[ArtworkImage] = None,
        status_code: int = 1,
        error_message: str = "") -> ArtworkData:
    artwork_data = ArtworkData()
    if error_message != "":
        artwork_data.is_error = True
        artwork_data.message = error_message
        if status_code == 1:
            status_code = 0
        artwork_data.status_code = status_code
    artwork_data.artwork_info = artwork_info
    artwork_data.artwork_info = artwork_image
    return artwork_data
