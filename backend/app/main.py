from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logger import setup_logging
from backend.app.presentation.api import auth_router, user_router, transaction_router, block_router, wallet_router, node_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(json_logs=(settings.app_env == "production"))
    logger.info("Starting VeriLedger API", env=settings.app_env)
    yield
    logger.info("Shutting down VeriLedger API")


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="VeriLedger API",
    description="Verifiable Finance Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(wallet_router.router)
app.include_router(transaction_router.router)
app.include_router(block_router.router)
app.include_router(node_router.router)


class HealthCheckResponse(BaseModel):
    status: str
    environment: str


@app.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        environment=settings.app_env,
    )
