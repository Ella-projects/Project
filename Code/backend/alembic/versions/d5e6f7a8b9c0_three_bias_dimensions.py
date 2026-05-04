"""three_bias_dimensions

Extends the bias model from a single s_bias D-score to three per-dimension
scores (age, gender, race) to match the expanded three-IAT assessment protocol.

Changes:
  users        — drop s_bias, add s_bias_age / s_bias_gender / s_bias_race
  iat_results  — add bias_type (age | gender | race)
  iat_trials   — add bias_type (age | gender | race)

Revision ID: d5e6f7a8b9c0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.drop_column("users", "s_bias")
    op.add_column("users", sa.Column("s_bias_age",    sa.Float(), nullable=True))
    op.add_column("users", sa.Column("s_bias_gender", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("s_bias_race",   sa.Float(), nullable=True))

    # ── iat_results ───────────────────────────────────────────────────────────
    op.add_column(
        "iat_results",
        sa.Column(
            "bias_type",
            sa.String(16),
            nullable=False,
            server_default="age",
            comment="age | gender | race",
        ),
    )

    # ── iat_trials ────────────────────────────────────────────────────────────
    op.add_column(
        "iat_trials",
        sa.Column(
            "bias_type",
            sa.String(16),
            nullable=False,
            server_default="age",
            comment="age | gender | race",
        ),
    )


def downgrade() -> None:
    # ── iat_trials ────────────────────────────────────────────────────────────
    op.drop_column("iat_trials", "bias_type")

    # ── iat_results ───────────────────────────────────────────────────────────
    op.drop_column("iat_results", "bias_type")

    # ── users — restore single s_bias, drop three-dimension columns ───────────
    op.drop_column("users", "s_bias_race")
    op.drop_column("users", "s_bias_gender")
    op.drop_column("users", "s_bias_age")
    op.add_column("users", sa.Column("s_bias", sa.Float(), nullable=True))
