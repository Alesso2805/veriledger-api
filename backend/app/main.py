import re
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logger import setup_logging
from backend.app.infrastructure import database
from backend.app.presentation.api import (
    auth_router,
    block_router,
    node_router,
    transaction_router,
    user_router,
    wallet_router,
)

logger = structlog.get_logger()

# A caller's request id is kept only when it is safe to write into a log line
REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(json_logs=(settings.app_env == "production"))
    logger.info("Starting VeriLedger API", env=settings.app_env)
    yield
    logger.info("Shutting down VeriLedger API")


app = FastAPI(
    title="VeriLedger API",
    description="Verifiable Finance Backend API",
    version="0.1.0",
    lifespan=lifespan,
    root_path=settings.api_root_path,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tag_each_request(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming if REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
    # Every log line of this request carries its id (VLA-26)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request handled",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return response


app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(wallet_router.router)
app.include_router(transaction_router.router)
app.include_router(block_router.router)
app.include_router(node_router.router)


class HealthCheckResponse(BaseModel):
    status: str
    environment: str
    # Lets the webapp offer "Try the demo" only where POST /auth/demo exists
    demo_mode: bool
    # "ok" when the database answered a query, "unreachable" otherwise (VLA-26)
    database: str


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    responses={503: {"model": HealthCheckResponse, "description": "The database does not answer"}},
)
async def health_check() -> HealthCheckResponse | JSONResponse:
    # Readiness: the node can serve requests only while its database answers, so the image's HEALTHCHECK says so too
    if await database.database_answers():
        return HealthCheckResponse(
            status="ok", environment=settings.app_env, demo_mode=settings.demo_mode, database="ok"
        )
    unavailable = HealthCheckResponse(
        status="unavailable", environment=settings.app_env, demo_mode=settings.demo_mode, database="unreachable"
    )
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=unavailable.model_dump())
