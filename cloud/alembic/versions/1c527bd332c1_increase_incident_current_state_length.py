"""increase incident current_state length

Revision ID: 1c527bd332c1
Revises: 001_initial_schema
Create Date: 2026-08-08 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1c527bd332c1'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'incidents',
        'current_state',
        existing_type=sa.String(length=100),
        type_=sa.Text(),
        existing_nullable=False,
        existing_server_default=''
    )


def downgrade() -> None:
    op.alter_column(
        'incidents',
        'current_state',
        existing_type=sa.Text(),
        type_=sa.String(length=100),
        existing_nullable=False,
        existing_server_default=''
    )
