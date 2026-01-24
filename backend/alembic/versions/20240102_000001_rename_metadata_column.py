"""Rename metadata column to extra_metadata in datasets table.

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename 'metadata' column to 'extra_metadata' in datasets table
    # The column was named 'metadata' in the initial migration but
    # SQLAlchemy model uses 'extra_metadata' to avoid conflict with
    # SQLAlchemy's reserved 'metadata' attribute
    op.alter_column(
        'datasets',
        'metadata',
        new_column_name='extra_metadata'
    )


def downgrade() -> None:
    # Rename back to 'metadata'
    op.alter_column(
        'datasets',
        'extra_metadata',
        new_column_name='metadata'
    )
