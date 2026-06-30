from dataclasses import asdict

from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL


class TableInfoMapper:
    @staticmethod
    def to_entity(table_info: TableInfoMySQL) -> TableInfo:
        return TableInfo(
            id=table_info.id or "",
            name=table_info.name or "",
            role=table_info.role or "",
            description=table_info.description or "",
        )

    @staticmethod
    def to_model(table_info: TableInfo) -> TableInfoMySQL:
        return TableInfoMySQL(**asdict(table_info))