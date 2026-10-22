import asyncio
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.domain.entities.user import User
from backend.app.infrastructure.limits.sliding_window import SlidingWindowLimiter
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl

MINUTE = 60.0
HOUR = 3600.0

# One per process, like the API itself; a restart starts every count again
limiter = SlidingWindowLimiter()
mining_lock = asyncio.Lock()


def too_many_requests(detail: str, retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
    )


def client_address(request: Request) -> str:
    # Behind Caddy this is the visitor's address only because the API trusts Caddy's X-Forwarded-For
    # (FORWARDED_ALLOW_IPS, SPEC › Demo limits)
    return request.client.host if request.client else "unknown"


async def enforce_demo_account_limits(request: Request, db: AsyncSession) -> None:
    if settings.demo_max_active_accounts:
        now = datetime.now(UTC)
        active, next_expiry = await UserRepositoryImpl(db).active_demo_accounts(now)
        if active >= settings.demo_max_active_accounts:
            # A place frees up when the oldest active demo expires
            retry_after = (next_expiry - now).total_seconds() if next_expiry else HOUR
            raise too_many_requests("The demo is full right now; try again later", retry_after)
    if settings.demo_accounts_per_ip_per_hour:
        key = f"demo accounts from {client_address(request)}"
        retry = limiter.hit(key, settings.demo_accounts_per_ip_per_hour, HOUR)
        if retry is not None:
            raise too_many_requests("Too many demo accounts from your network in the last hour; try again later", retry)


def enforce_demo_mining_limit(user: User) -> None:
    if not user.is_demo or not settings.demo_mines_per_hour:
        return
    limit = settings.demo_mines_per_hour
    retry_after = limiter.hit(f"mining by {user.id}", limit, HOUR)
    if retry_after is not None:
        blocks = "block" if limit == 1 else "blocks"
        raise too_many_requests(f"A demo account can mine {limit} {blocks} per hour; try again later", retry_after)


def enforce_login_limit(request: Request) -> None:
    # Every attempt counts, so guessing passwords costs a minute per few tries
    if not settings.login_attempts_per_minute:
        return
    retry_after = limiter.hit(f"sign-ins from {client_address(request)}", settings.login_attempts_per_minute, MINUTE)
    if retry_after is not None:
        raise too_many_requests("Too many sign-in attempts from your network; try again in a minute", retry_after)


def enforce_transaction_limit(sender_address: str) -> None:
    if not settings.transactions_per_sender_per_minute:
        return
    limit = settings.transactions_per_sender_per_minute
    retry_after = limiter.hit(f"transactions from {sender_address}", limit, MINUTE)
    if retry_after is not None:
        raise too_many_requests("Too many transactions from this sender; try again in a minute", retry_after)


@asynccontextmanager
async def one_mine_at_a_time() -> AsyncIterator[None]:
    """A second mining request answers 429 at once instead of racing the first one to the same height."""
    if not settings.mine_one_at_a_time:
        yield
        return
    # No await between the check and the acquire, so two requests cannot both pass
    if mining_lock.locked():
        raise too_many_requests("A block is being mined on this node; try again in a moment", 1)
    async with mining_lock:
        yield
