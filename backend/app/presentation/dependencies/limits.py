import math
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.domain.entities.user import User
from backend.app.infrastructure.limits.sliding_window import SlidingWindowLimiter
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl

HOUR = 3600.0

# One per process, like the API itself; a restart starts every count again
demo_limiter = SlidingWindowLimiter()


def too_many_requests(detail: str, retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
    )


async def enforce_demo_account_limits(request: Request, db: AsyncSession) -> None:
    if settings.demo_max_active_accounts:
        now = datetime.now(UTC)
        active, next_expiry = await UserRepositoryImpl(db).active_demo_accounts(now)
        if active >= settings.demo_max_active_accounts:
            # A place frees up when the oldest active demo expires
            retry_after = (next_expiry - now).total_seconds() if next_expiry else HOUR
            raise too_many_requests("The demo is full right now; try again later", retry_after)
    if settings.demo_accounts_per_ip_per_hour:
        # Behind Caddy this is the visitor's address only with uvicorn's --proxy-headers (SPEC › Demo limits)
        client = request.client.host if request.client else "unknown"
        retry = demo_limiter.hit(f"demo accounts from {client}", settings.demo_accounts_per_ip_per_hour, HOUR)
        if retry is not None:
            raise too_many_requests("Too many demo accounts from your network in the last hour; try again later", retry)


def enforce_demo_mining_limit(user: User) -> None:
    # Only demo accounts are limited
    if user.expires_at is None or not settings.demo_mines_per_hour:
        return
    limit = settings.demo_mines_per_hour
    retry_after = demo_limiter.hit(f"mining by {user.id}", limit, HOUR)
    if retry_after is not None:
        blocks = "block" if limit == 1 else "blocks"
        raise too_many_requests(f"A demo account can mine {limit} {blocks} per hour; try again later", retry_after)
