"""add_nudge_order_and_tracking

Within-subjects crossover design:
- ClinicalSession gains nudge_order ('control_first' | 'treatment_first')
  assigned by user_id parity so the two groups are counterbalanced.
- CaseDecision gains nudge_active (bool), nudge_fired (bool), nudge_outcome (str).

Revision ID: a1b2c3d4e5f6
Revises: f420358dd3a0
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f420358dd3a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ClinicalSession: within-subjects crossover order
    op.add_column('clinical_sessions',
        sa.Column(
            'nudge_order', sa.String(length=16), nullable=False,
            server_default='control_first',
            comment="Crossover order: 'control_first' | 'treatment_first'"
        )
    )

    # CaseDecision: per-case phase marker + nudge outcome tracking
    op.add_column('case_decisions',
        sa.Column(
            'nudge_active', sa.Boolean(), nullable=False, server_default=sa.false(),
            comment="True = treatment phase (nudges were active); False = control phase"
        )
    )
    op.add_column('case_decisions',
        sa.Column(
            'nudge_fired', sa.Boolean(), nullable=False, server_default=sa.false(),
            comment="True when a Hard Nudge intercepted Submit for this case"
        )
    )
    op.add_column('case_decisions',
        sa.Column(
            'nudge_outcome', sa.String(length=32), nullable=True,
            comment="'changed_correct' | 'changed_incorrect' | 'unchanged' | null"
        )
    )


def downgrade() -> None:
    op.drop_column('case_decisions', 'nudge_outcome')
    op.drop_column('case_decisions', 'nudge_fired')
    op.drop_column('case_decisions', 'nudge_active')
    op.drop_column('clinical_sessions', 'nudge_order')
