from typing import Iterable
from mysql.connector.pooling import MySQLConnectionPool

from src.base.model.newartwork import AuditType, ArtworkInfo

class AuditService:

    def __init__(self, host="127.0.0.1", port=3306, user="", password="", database=""):
        self.sql_pool = MySQLConnectionPool(pool_name="",
                                            pool_size=10,
                                            pool_reset_session=False,
                                            host=host,
                                            port=port,
                                            user=user,
                                            password=password,
                                            database=database)

    def get_art_for_audit(self, audit_type: AuditType) -> Iterable[ArtworkInfo]:
        """
        :param audit_type: 从数据库获取到未审核的数据
        :return: 返回带有作品具体信息的列表
        """