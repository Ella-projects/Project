"""add_nudge_count_columns_to_sessions

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-28 17:36:11.408170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinical_sessions", sa.Column("hard_nudge_count",    sa.Float(), nullable=False, server_default="0"))
    op.add_column("clinical_sessions", sa.Column("hard_nudge_accepted", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("clinical_sessions", "hard_nudge_accepted")
    op.drop_column("clinical_sessions", "hard_nudge_count")
