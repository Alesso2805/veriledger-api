from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
import structlog
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logger import setup_logging

logger = structlog.get_logger()

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
)

class HealthCheckResponse(BaseModel):
    status: str
    environment: str

@app.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        environment=settings.app_env,
    )
