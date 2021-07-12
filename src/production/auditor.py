# audit.py
#
# Makes decisions on image status


from src.model.artwork import AuditType, AuditStatus, AuditInfo


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

