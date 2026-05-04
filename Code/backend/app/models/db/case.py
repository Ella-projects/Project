from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Float, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TriageCase(Base):
    """
    A clinical triage case presented to the clinician.
    counter_stereotypical cases are the experimental stimuli used to
    trigger heuristic shortcuts and measure ΔAcc.
    """

    __tablename__ = "triage_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_label: Mapped[str] = mapped_column(String(64), nullable=False)
    chief_complaint: Mapped[str] = mapped_column(String(256), nullable=False)

    # JSON-encoded vitals dict e.g. '{"HR": "102 bpm", "BP": "148/92 mmHg"}'
    vitals_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Newline-separated objective findings
    objective_findings: Mapped[str] = mapped_column(Text, nullable=False)

    # Ground truth for ΔAcc calculation
    correct_decision: Mapped[str] = mapped_column(String(16), nullable=False)

    is_counter_stereotypical: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Experimental stimulus — demographically counter-stereotypical presentation"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CaseDecision(Base):
    """Records the clinician's triage decision for a case in a session."""

    __tablename__ = "case_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("clinical_sessions.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(ForeignKey("triage_cases.id"), nullable=False)

    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_counter_stereotypical: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Window id at time of decision (for nudge correlation)
    window_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Whether nudges were active when this case was presented (crossover phase marker)
    nudge_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True = treatment phase; False = control phase for this case"
    )

    # Nudge outcome tracking — populated when a Hard Nudge fired before this decision
    nudge_fired: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True when a Hard Nudge intercepted the Submit for this case"
    )
    pre_nudge_decision: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True,
        comment="Decision the clinician had selected before the Hard Nudge modal appeared"
    )
    nudge_outcome: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True,
        comment="'changed_correct'|'changed_incorrect'|'unchanged' — null when no nudge fired"
    )

    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
