# audit.py
#
# Makes decisions on image status


from src.model.artwork import AuditType, AuditStatus, AuditInfo


class ArtworkStatusUpdate:

    def __init__(self, audit_info: AuditInfo, status: AuditStatus, type: AuditType = None, reason: str = None):
        self.audit_info = audit_info
        self.new_status = status.value if isinstance(status, AuditStatus) else status
        self.new_type = type.value if isinstance(type, AuditType) else type
        self.new_reason = reason


class Auditor:

    @staticmethod
    def audit(
            audit_info: AuditInfo,
            new_status: AuditStatus,
            new_type: str = None,
            new_reason: str = None
    ):
        if new_type is None:
            new_type = audit_info.audit_type
        if new_reason is None:
            new_reason = audit_info.audit_reason
        return ArtworkStatusUpdate(audit_info, new_status, new_type, new_reason)

