"""add_pre_nudge_decision_to_case_decisions

Revision ID: e1f2a3b4c5d6
Revises: d5e6f7a8b9c0
Create Date: 2026-04-28 17:30:26.982820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "case_decisions",
        sa.Column(
            "pre_nudge_decision",
            sa.String(16),
            nullable=True,
            comment="Decision selected before the Hard Nudge modal — null when no nudge fired",
        ),
    )


def downgrade() -> None:
    op.drop_column("case_decisions", "pre_nudge_decision")
