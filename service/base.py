from model.artwork import AuditInfo, AuditType, AuditStatus


def CreateArtworkAuditInfoFromSQLData(data: tuple) -> AuditInfo:
    (site, connection_id, type_status, status, reason) = data
    return AuditInfo(site=site,
                     connection_id=connection_id,
                     type_status=AuditType(type_status),
                     status=AuditStatus(status),
                     reason=reason
                     )
