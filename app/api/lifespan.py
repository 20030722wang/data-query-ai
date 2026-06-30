from contextlib import asynccontextmanager

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger


@asynccontextmanager
async def lifespan(app):
    try:
        qdrant_client_manager.init()
        embedding_client_manager.init()
        es_client_manager.init()
        meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()
        logger.info("All clients initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        raise RuntimeError(f"Startup failed: {e}") from e
    yield
    await qdrant_client_manager.close()
    await es_client_manager.close()
    await embedding_client_manager.close()
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    logger.info("All clients closed")


