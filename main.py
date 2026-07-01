"""DataQuery AI — Natural Language to SQL with LangGraph + FastAPI + Vue 3."""

import os
import sys
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Fix garbled Chinese output on Windows (stdout defaults to gbk)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from app.api.lifespan import lifespan  # noqa: E402
from app.api.routers.query_router import query_router  # noqa: E402
from app.api.schemas.error_schema import ErrorResponse  # noqa: E402
from app.core.context import request_id_context_var  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.core.log import logger  # noqa: E402

app = FastAPI(
    title="DataQuery AI",
    description="自然语言转 SQL 的智能数据查询助手",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
allow_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)


# ── Request ID Middleware ────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_context_var.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Exception Handlers ───────────────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = request_id_context_var.get("N/A")
    logger.warning(f"Application error [{exc.code}]: {exc}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            request_id=request_id,
            code=exc.code,
            message=str(exc) or exc.code,
            detail=exc.detail,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_context_var.get("N/A")
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            request_id=request_id,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            detail=str(exc),
        ).model_dump(),
    )
