from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Float, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClinicalSession(Base):
    """One triage session for a user. Tracks fatigue and rule adherence."""

    __tablename__ = "clinical_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    delta_acc: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Diagnostic accuracy delta vs baseline"
    )
    hard_nudge_count: Mapped[int] = mapped_column(
        Float, default=0, nullable=False,
        comment="Total hard nudges fired this session"
    )
    hard_nudge_accepted: Mapped[int] = mapped_column(
        Float, default=0, nullable=False,
        comment="Hard nudges where user changed their decision"
    )
    rule_adherence_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="hard_nudge_accepted / hard_nudge_count — null until first hard nudge"
    )

    # Within-subjects crossover order — assigned at session start by user_id parity
    # so each user's cohort is counterbalanced.
    # "control_first":   cases 1-N/2 = no nudges, cases N/2+1-N = nudges
    # "treatment_first": cases 1-N/2 = nudges,    cases N/2+1-N = no nudges
    nudge_order: Mapped[str] = mapped_column(
        String(16), default="control_first", nullable=False,
        comment="Crossover order: 'control_first' | 'treatment_first'"
    )

    # Rolling fatigue coefficient W_fatigue ∈ [0, 1]
    w_fatigue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
