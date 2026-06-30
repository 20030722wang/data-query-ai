import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class DWMysqlRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _validate_identifier(name: str) -> str:
        """Validate and sanitize a SQL identifier (table or column name)."""
        name = name.strip()
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"Invalid SQL identifier: {name!r}")
        return name

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        table_name = self._validate_identifier(table_name)
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()
        # [{'Field': 'order_id', 'Type': 'varchar(30)', 'Null': 'NO', 'Key': 'PRI', 'Default': None, 'Extra': 'auto_increment'},
        #  {'Field': 'customer_id', 'Type': 'varchar(30)', 'Null': 'NO', 'Key': 'MUL', 'Default': None, 'Extra': ''}]
        return {row['Field']: row['Type'] for row in result_dict}
        # {order_id:varchar(30),customer_id:varchar(30)}

    async def get_column_values(self, table_name: str, column_name: str, limit: int = 10):
        table_name = self._validate_identifier(table_name)
        column_name = self._validate_identifier(column_name)
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self):
        sql = "select version()"
        result = await self.session.execute(text(sql))
        version = result.scalar()

        bind = self.session.get_bind()
        dialect = bind.dialect.name if bind is not None else "unknown"
        return {"dialect": dialect, "version": version}

    async def validate(self, sql: str):
        sql = f"explain {sql}"
        await self.session.execute(text(sql))

    async def run(self, sql: str) -> list[dict]:
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
