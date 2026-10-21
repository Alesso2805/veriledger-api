"""Demo accounts: no email or password, and an expiry

Revision ID: 5d2b8e41c7a9
Revises: 9c1e5b7a3d24
Create Date: 2026-10-21 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d2b8e41c7a9'
down_revision: Union[str, None] = '9c1e5b7a3d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_expires_at'), 'users', ['expires_at'], unique=False)
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=True)
    op.alter_column('users', 'password_hash', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Demo accounts have neither an email nor a password, so they cannot stay once both are NOT NULL again
    op.execute("DELETE FROM users WHERE email IS NULL OR password_hash IS NULL")
    op.alter_column('users', 'password_hash', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=False)
    op.drop_index(op.f('ix_users_expires_at'), table_name='users')
    op.drop_column('users', 'expires_at')
