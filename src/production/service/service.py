import pathlib

from src.base.model.newartwork import AuditType
from src.base.utils.namemap import NameMap


class AuditService:

    def __init__(self, sql_config=None):
        name_map_file = pathlib.Path(__file__).parent.joinpath("../../../data/namemap.json").resolve()
        self.name_map = NameMap(name_map_file)

    def audit_start(self, audit_type: AuditType) -> int:
        """
        :param audit_type: 设置审核的类型，并对审核进行初始化
        :return: 审核数量
        """
        # 1. Get from database  从数据库获取到要审核的数据