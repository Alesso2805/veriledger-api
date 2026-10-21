from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.infrastructure.models.transaction_model import TransactionModel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("column", ["amount", "fee"])
async def test_the_models_refuse_a_negative_amount_or_fee_as_the_migrations_do(
    postgres: async_sessionmaker[AsyncSession], column: str
) -> None:
    # The integration tests build their schema from the models, so the models must carry the same CHECKs
    values = {"amount": 1.0, "fee": 0.0, column: -0.00000001}
    async with postgres() as session:
        session.add(
            TransactionModel(
                sender_address="a",
                receiver_address="b",
                status=TransactionStatus.PENDING,
                timestamp=datetime.now(UTC),
                signature="sig",
                **values,
            )
        )
        with pytest.raises(IntegrityError, match=f"ck_transactions_{column}_not_negative"):
            await session.flush()
