from dataclasses import asdict

from app.entities.column_info import ColumnInfo
from app.models.column_info import ColumnInfoMySQL

class ColumnInfoMapper:
    @staticmethod
    def to_entity(column_info_mysql: ColumnInfoMySQL) -> ColumnInfo:
        return ColumnInfo(
            id=column_info_mysql.id or "",
            name=column_info_mysql.name or "",
            type=column_info_mysql.type or "",
            role=column_info_mysql.role or "",
            examples=column_info_mysql.examples if isinstance(column_info_mysql.examples, list) else [],
            description=column_info_mysql.description or "",
            alias=column_info_mysql.alias if isinstance(column_info_mysql.alias, list) else [],
            table_id=column_info_mysql.table_id or "",
        )

    @staticmethod
    def to_model(column_info: ColumnInfo) -> ColumnInfoMySQL:
        return ColumnInfoMySQL(**asdict(column_info))