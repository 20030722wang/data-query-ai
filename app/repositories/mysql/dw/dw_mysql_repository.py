"""Data Warehouse repository — read-only SQL execution with safety guards."""

import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.exceptions import NoSQLReadOnlyError

_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Whitelist of SQL statement prefixes that are safe for read-only execution
_READONLY_PREFIXES = frozenset({"SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC", "WITH"})

# Maximum rows to return when the query has no explicit LIMIT
_DEFAULT_LIMIT = 10_000

_HAS_LIMIT_RE = re.compile(r'\bLIMIT\s+\d+', re.IGNORECASE)


class DWMysqlRepository:
    """Repository for executing read-only queries against the data warehouse.

    All SQL is validated against a read-only whitelist before execution.
    Results are automatically capped to prevent excessive memory usage.

    Args:
        session: An active SQLAlchemy AsyncSession bound to the DW database.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _validate_identifier(name: str) -> str:
        """Validate and sanitize a SQL identifier (table or column name)."""
        name = name.strip()
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"Invalid SQL identifier: {name!r}")
        return name

    @staticmethod
    def _guard_read_only(sql: str) -> str:
        """Reject non-read-only SQL statements before execution.

        Args:
            sql: The raw SQL string to validate.

        Returns:
            The input SQL if it passes the read-only check.

        Raises:
            NoSQLReadOnlyError: If the SQL starts with a disallowed keyword.
        """
        stripped = sql.strip()
        first_word = stripped.split(maxsplit=1)[0].upper() if stripped else ""
        for allowed in _READONLY_PREFIXES:
            if stripped.upper().startswith(allowed):
                return sql
        raise NoSQLReadOnlyError(
            f"Only read-only SQL is permitted. "
            f"Statement starts with '{first_word}'. "
            f"Allowed prefixes: {', '.join(sorted(_READONLY_PREFIXES))}",
        )

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        """Retrieve column name → MySQL type mapping for a table."""
        table_name = self._validate_identifier(table_name)
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        rows = result.mappings().fetchall()
        return {row['Field']: row['Type'] for row in rows}

    async def get_column_values(
        self, table_name: str, column_name: str, limit: int = 10,
    ):
        """Retrieve distinct values for a single column."""
        table_name = self._validate_identifier(table_name)
        column_name = self._validate_identifier(column_name)
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self) -> dict[str, str | None]:
        """Return database dialect and version string."""
        sql = "select version()"
        result = await self.session.execute(text(sql))
        version = result.scalar()
        bind = self.session.get_bind()
        dialect = bind.dialect.name if bind is not None else "unknown"
        return {"dialect": dialect, "version": version}

    async def validate(self, sql: str) -> None:
        """Run EXPLAIN on a read-only SQL statement to check syntax."""
        sql = self._guard_read_only(sql)
        await self.session.execute(text(f"explain {sql}"))

    async def run(self, sql: str) -> list[dict]:
        """Execute a read-only SQL statement and return the result set.

        Applies a row limit if none is present, and rejects any
        non-read-only statement before execution.

        Args:
            sql: The SQL SELECT (or WITH/EXPLAIN/SHOW/DESCRIBE) statement.

        Returns:
            A list of row dicts from the result set.

        Raises:
            NoSQLReadOnlyError: If the SQL is not read-only.
            SQLExecutionError: If the query fails at the database level.
        """
        sql = self._guard_read_only(sql)
        if not _HAS_LIMIT_RE.search(sql):
            sql = f"({sql}) limit {_DEFAULT_LIMIT}"
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
