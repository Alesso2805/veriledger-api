"""Amount and fee are never negative

Revision ID: 7a3f9c2e1b64
Revises: 5d2b8e41c7a9
Create Date: 2026-10-21 20:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7a3f9c2e1b64'
down_revision: Union[str, None] = '5d2b8e41c7a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint('ck_transactions_amount_not_negative', 'transactions', 'amount >= 0')
    op.create_check_constraint('ck_transactions_fee_not_negative', 'transactions', 'fee >= 0')


def downgrade() -> None:
    op.drop_constraint('ck_transactions_fee_not_negative', 'transactions', type_='check')
    op.drop_constraint('ck_transactions_amount_not_negative', 'transactions', type_='check')
