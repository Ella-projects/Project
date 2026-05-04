from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Float, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TelemetryWindow(Base):
    """
    Processed 5-second kinematic window — one row in the Rough Set universe U.
    Each instance corresponds to one temporal window of mouse telemetry.
    """

    __tablename__ = "telemetry_windows"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("clinical_sessions.id"), nullable=False
    )

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    point_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Kinematic features (attributes in the Rough Set information system)
    tortuosity: Mapped[float] = mapped_column(
        Float, nullable=False, comment="τ = actual path length / straight-line displacement"
    )
    mean_velocity: Mapped[float] = mapped_column(Float, nullable=False)
    velocity_variance: Mapped[float] = mapped_column(Float, nullable=False)
    acceleration_variance: Mapped[float] = mapped_column(Float, nullable=False)

    stutter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tau_deviation: Mapped[float] = mapped_column(
        Float, nullable=False, comment="(τ - baseline_mean) / baseline_std"
    )
    time_on_task: Mapped[float] = mapped_column(Float, nullable=False)

    # Rough Set classification output
    rs_classification: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Risk score P = W_fatigue × S_bias applied at this window
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
