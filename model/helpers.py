from typing import List

from model.artwork import ArtworkInfo, ArtworkImage, AuditInfo
from model.containers import ArtworkAuditData, ArtworkData, ArtworkPushData


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
            artwork_push_data.status_code = 0
        else:
            artwork_push_data.status_code = status_code
    artwork_push_data.artwork_info = artwork_info
    artwork_push_data.artwork_image = artwork_image
    artwork_push_data.count = count
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
            artwork_audit_data.status_code = 0
        else:
            artwork_audit_data.status_code = status_code
    artwork_audit_data.artwork_info = artwork_info
    artwork_audit_data.artwork_image = artwork_image
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
            artwork_data.status_code = 0
        else:
            artwork_data.status_code = status_code
    artwork_data.artwork_info = artwork_info
    artwork_data.artwork_image = artwork_image
    return artwork_data
