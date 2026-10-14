from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from saas import __version__
from saas.api import admin_routes, auth_routes, billing_routes, chat_routes, documents_routes, health, widget_routes
from saas.core.config import settings
from saas.core.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info(
        "startup",
        version=__version__,
        auth=settings.auth_provider,
        billing=settings.billing_provider,
    )
    yield
    log.info("shutdown")


app = FastAPI(
    title="GroundTruth",
    version=__version__,
    description=(
        "GroundTruth: Multi-tenant AI assistant grounded in documentation with "
        "per-tenant RAG isolation (Postgres RLS), streaming chat with citations, "
        "admin dashboard, embeddable widget, plan-based limits."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        log.exception("unhandled", error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "internal", "request_id": request_id})
    elapsed = (time.perf_counter() - start) * 1000
    response.headers["x-request-id"] = request_id
    response.headers["x-response-time-ms"] = f"{elapsed:.1f}"
    log.info("request", status=response.status_code, elapsed_ms=round(elapsed, 1))
    return response


app.include_router(health.router)
app.include_router(auth_routes.router)
app.include_router(documents_routes.router)
app.include_router(chat_routes.router)
app.include_router(billing_routes.router)
app.include_router(admin_routes.router)
app.include_router(widget_routes.router)

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
