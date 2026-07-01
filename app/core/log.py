"""Centralized logging configuration using Loguru.

Logger configuration is deferred (call ``configure_logging()`` explicitly
from the lifespan startup hook) to avoid import-time side effects.
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.context import request_id_context_var

_logger_configured: bool = False

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>request_id - {extra[request_id]}</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def inject_request_id(record: dict) -> bool:
    """Patch log record to include the current request ID from context."""
    request_id = request_id_context_var.get("N/A")
    record["extra"]["request_id"] = request_id
    return True


def configure_logging(app_config) -> None:
    """Idempotent logger setup — call once from the lifespan startup hook.

    Args:
        app_config: The AppConfig dataclass loaded from YAML.
    """
    global _logger_configured
    if _logger_configured:
        return

    logger.remove()
    logger.patch(inject_request_id)

    if app_config.logging.console.enable:
        logger.add(
            sink=sys.stdout,
            level=app_config.logging.console.level,
            format=LOG_FORMAT,
        )

    if app_config.logging.file.enable:
        path = Path(app_config.logging.file.path)
        path.mkdir(parents=True, exist_ok=True)
        logger.add(
            sink=path / "app.log",
            level=app_config.logging.file.level,
            format=LOG_FORMAT,
            rotation=app_config.logging.file.rotation,
            retention=app_config.logging.file.retention,
            encoding="utf-8",
        )

    _logger_configured = True
