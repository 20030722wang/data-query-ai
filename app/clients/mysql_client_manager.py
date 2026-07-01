"""MySQL async client manager with configurable connection pool."""

import os
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker

from app.conf.app_config import DBConfig, app_config


class MysqlClientManager:
    """Manages an async MySQL engine + session factory for one database.

    Pool size and overflow are configurable via environment variables
    (``DB_POOL_SIZE``, ``DB_MAX_OVERFLOW``) to accommodate production
    workloads without code changes.

    Args:
        db_config: Database connection parameters from app config.
    """

    def __init__(self, db_config: DBConfig) -> None:
        self.db_config = db_config
        self.engine: Optional[AsyncEngine] = None
        self.session_factory = None

    def _get_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.db_config.user}:{self.db_config.password}"
            f"@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}"
            f"?charset=utf8mb4"
        )

    def init(self) -> None:
        pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.engine = create_async_engine(
            url=self._get_url(),
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            autoflush=True,
            expire_on_commit=False,
            autobegin=True,
        )

    async def close(self) -> None:
        await self.engine.dispose()


dw_mysql_client_manager = MysqlClientManager(app_config.db_dw)
meta_mysql_client_manager = MysqlClientManager(app_config.db_meta)
