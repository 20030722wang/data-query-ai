"""API routes — query submission and health check."""

import asyncio
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.core.exceptions import QueryTooLongError, QueryTooShortError
from app.core.log import logger
from app.services.query_service import QueryService

query_router = APIRouter()

_START_TIME: float = time.time()


# ── Health Check ─────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    uptime_seconds: float
    checks: dict[str, str]


@query_router.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Liveness probe — checks connectivity to upstream databases."""
    checks: dict[str, str] = {}
    for name, manager in [
        ("mysql_meta", meta_mysql_client_manager),
        ("mysql_dw", dw_mysql_client_manager),
    ]:
        try:
            async with manager.session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks[name] = "ok"
        except Exception as e:
            checks[name] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        uptime_seconds=time.time() - _START_TIME,
        checks=checks,
    )


# ── Query ────────────────────────────────────────────────────────────────────
@query_router.post("/api/v1/query")
async def query_handler(
    query: QuerySchema,
    query_service: Annotated[QueryService, Depends(get_query_service)],
):
    """Submit a natural-language query and receive a streaming SSE response."""
    q = query.query.strip()

    if not q:
        raise QueryTooShortError("Query must not be empty")
    if len(q) > 1000:
        raise QueryTooLongError(f"Query must be ≤1000 characters, got {len(q)}")

    async def _stream_with_cleanup():
        gen = query_service.query(q)
        try:
            async for chunk in gen:
                yield chunk
        except asyncio.CancelledError:
            logger.warning(f"Client disconnected for query: {q[:80]}...")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Request cancelled'})}\n\n"
            raise

    return StreamingResponse(_stream_with_cleanup(), media_type="text/event-stream")
