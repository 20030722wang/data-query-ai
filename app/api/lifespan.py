"""FastAPI lifespan handler — manages service client lifecycle."""

from contextlib import asynccontextmanager

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.app_config import app_config
from app.core.log import configure_logging, logger


@asynccontextmanager
async def lifespan(app):
    configure_logging(app_config)

    init_errors: list[str] = []
    for name, manager in [
        ("qdrant", qdrant_client_manager),
        ("embedding", embedding_client_manager),
        ("elasticsearch", es_client_manager),
        ("mysql_meta", meta_mysql_client_manager),
        ("mysql_dw", dw_mysql_client_manager),
    ]:
        try:
            manager.init()
        except Exception as e:
            init_errors.append(f"{name}: {e}")
            logger.warning(f"Failed to initialize {name}: {e}")

    if init_errors:
        logger.error(f"Startup errors: {'; '.join(init_errors)}")
        raise RuntimeError(f"Startup failed: {'; '.join(init_errors)}")

    logger.info("All clients initialized successfully")
    yield

    for name, manager in [
        ("qdrant", qdrant_client_manager),
        ("elasticsearch", es_client_manager),
        ("embedding", embedding_client_manager),
        ("mysql_meta", meta_mysql_client_manager),
        ("mysql_dw", dw_mysql_client_manager),
    ]:
        try:
            await manager.close()
        except Exception as e:
            logger.warning(f"Error closing {name}: {e}")

    logger.info("All clients closed")
