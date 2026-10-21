"""Add nonce to transactions

Revision ID: 9c1e5b7a3d24
Revises: ae3c16a02c57
Create Date: 2026-10-21 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1e5b7a3d24'
down_revision: Union[str, None] = 'ae3c16a02c57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('nonce', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('uq_transactions_sender_nonce', 'transactions', ['sender_address', 'nonce'])


def downgrade() -> None:
    op.drop_constraint('uq_transactions_sender_nonce', 'transactions', type_='unique')
    op.drop_column('transactions', 'nonce')
