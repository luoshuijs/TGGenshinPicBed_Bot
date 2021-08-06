# audit.py
#
# Makes decisions on image status


from src.base.bean.artwork import AuditType, AuditStatus, AuditInfo


class ArtworkStatusUpdate:

    def __init__(self, audit_info: AuditInfo, status: AuditStatus, type: AuditType = None, reason: str = None):
        self.audit_info = audit_info
        self.new_status = AuditStatus(status).value
        self.new_type = AuditType(type).value if type is not None else None
        self.new_reason = reason

    def can_update(self):
        if self.audit_info is None:
            return False
        a = self.audit_info
        audit_status = a.audit_status.value if a.audit_status is not None else None
        audit_type = a.audit_type.value if a.audit_type is not None else None
        audit_reason = a.audit_reason
        return (self.new_status != audit_status
            or self.new_type != audit_type
            or self.new_reason != audit_reason
        )


def approve(audit_info: AuditInfo):
    new_status = AuditStatus.PASS
    new_type = AuditType.SFW
    if not check_can_audit(audit_info, new_status):
        return ArtworkStatusUpdate(audit_info, audit_info.audit_status, type=audit_info.audit_type)
    if audit_info.audit_type is not None:
        new_type = audit_info.audit_type
    return ArtworkStatusUpdate(audit_info, new_status, new_type)


def reject(audit_info: AuditInfo, reason: str = None):
    new_status = AuditStatus.REJECT
    new_type = AuditType.SFW
    new_reason = reason
    if not check_can_audit(audit_info, new_status):
        return ArtworkStatusUpdate(audit_info, audit_info.audit_status, type=audit_info.audit_type)
    if audit_info.audit_type is not None:
        new_type = audit_info.audit_type
    if reason == AuditType.NSFW.value:
        if new_type == AuditType.SFW:
            new_status = AuditStatus.INIT
            new_type = AuditType.NSFW
    elif reason == AuditType.R18.value:
        if new_type != AuditType.R18:
            new_status = AuditStatus.INIT
            new_type = AuditType.R18
    elif reason is None:
        new_reason = audit_info.audit_reason
    return ArtworkStatusUpdate(audit_info, new_status, type=new_type, reason=new_reason)


def push(audit_info):
    new_status = AuditStatus.PUSH
    if not check_can_audit(audit_info, new_status):
        return ArtworkStatusUpdate(audit_info, audit_info.audit_status, type=audit_info.audit_type)
    return ArtworkStatusUpdate(audit_info, new_status, type=audit_info.audit_type, reason=None)


def check_can_audit(audit_info, new_status: AuditStatus):
    if audit_info.audit_status is not None:
        if audit_info.audit_status != AuditStatus.INIT \
                and audit_info.audit_status != AuditStatus.PASS \
                and audit_info.audit_status != new_status:
            return False
    return True

