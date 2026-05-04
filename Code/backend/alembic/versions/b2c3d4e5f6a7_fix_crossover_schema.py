"""fix_crossover_schema

Replaces condition/nudge_enabled (from the old between-subjects design)
with nudge_order (within-subjects crossover), and adds nudge_active to
case_decisions if it doesn't exist yet.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── clinical_sessions ──────────────────────────────────────────────────────

    # Drop old between-subjects columns if they exist
    cols = {row[0] for row in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns "
                "WHERE table_name='clinical_sessions'")
    )}

    if 'condition' in cols:
        op.drop_column('clinical_sessions', 'condition')
    if 'nudge_enabled' in cols:
        op.drop_column('clinical_sessions', 'nudge_enabled')

    # Add nudge_order if missing
    if 'nudge_order' not in cols:
        op.add_column('clinical_sessions',
            sa.Column('nudge_order', sa.String(length=16), nullable=False,
                      server_default='control_first',
                      comment="Crossover order: 'control_first' | 'treatment_first'")
        )

    # ── case_decisions ─────────────────────────────────────────────────────────

    dcols = {row[0] for row in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns "
                "WHERE table_name='case_decisions'")
    )}

    if 'nudge_active' not in dcols:
        op.add_column('case_decisions',
            sa.Column('nudge_active', sa.Boolean(), nullable=False,
                      server_default=sa.false(),
                      comment="True = treatment phase; False = control phase")
        )
    if 'nudge_fired' not in dcols:
        op.add_column('case_decisions',
            sa.Column('nudge_fired', sa.Boolean(), nullable=False,
                      server_default=sa.false())
        )
    if 'nudge_outcome' not in dcols:
        op.add_column('case_decisions',
            sa.Column('nudge_outcome', sa.String(length=32), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('clinical_sessions', 'nudge_order')
    op.add_column('clinical_sessions',
        sa.Column('condition', sa.String(length=16), nullable=False, server_default='treatment'))
    op.add_column('clinical_sessions',
        sa.Column('nudge_enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.drop_column('case_decisions', 'nudge_active')
    op.drop_column('case_decisions', 'nudge_fired')
    op.drop_column('case_decisions', 'nudge_outcome')
