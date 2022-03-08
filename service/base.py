from model.artwork import AuditInfo, AuditType, AuditStatus


def CreateArtworkAuditInfoFromPixivSQLData(data: tuple, site: str) -> AuditInfo:
    (illusts_id, type_status, status, reason) = data
    return AuditInfo(site=site,
                     connection_id=illusts_id,
                     type_status=AuditType(type_status),
                     status=AuditStatus(status),
                     reason=reason
                     )


def CreateArtworkAuditInfoFromSQLData(data: tuple) -> AuditInfo:
    (site, connection_id, type_status, status, reason) = data
    return AuditInfo(site=site,
                     connection_id=connection_id,
                     type_status=AuditType(type_status),
                     status=AuditStatus(status),
                     reason=reason
                     )
