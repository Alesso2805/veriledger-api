from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.database import get_db_session

# scope="function" closes the session, and so commits, before the response is sent; the default for a
# dependency with yield closes it afterwards, when the client may already hold a 201 for a failed commit.
# FastAPI caches dependencies per scope, so every route and dependency uses this alias to share one session.
DbSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]
