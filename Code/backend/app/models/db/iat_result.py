from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Float, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IATTrial(Base):
    """Single trial within an IAT administration."""

    __tablename__ = "iat_trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("clinical_sessions.id"), nullable=False
    )

    bias_type: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="age",
        comment="age | gender | race"
    )

    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    trial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_practice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    stimulus_word: Mapped[str] = mapped_column(String(128), nullable=False)
    stimulus_category: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="e.g. 'pleasant', 'unpleasant', 'target_a', 'target_b'"
    )
    correct_key: Mapped[str] = mapped_column(String(8), nullable=False)

    response_key: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    reaction_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    presented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IATResult(Base):
    """
    Aggregated IAT result for a user.
    D-score computed per Greenwald et al. (2003) algorithm.
    """

    __tablename__ = "iat_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("clinical_sessions.id"), nullable=False
    )

    bias_type: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="age",
        comment="age | gender | race"
    )

    d_score: Mapped[float] = mapped_column(Float, nullable=False)

    mean_rt_block3: Mapped[float] = mapped_column(Float, nullable=False)
    mean_rt_block6: Mapped[float] = mapped_column(Float, nullable=False)
    mean_rt_block4: Mapped[float] = mapped_column(Float, nullable=False)
    mean_rt_block7: Mapped[float] = mapped_column(Float, nullable=False)
    pooled_sd_blocks3_6: Mapped[float] = mapped_column(Float, nullable=False)
    pooled_sd_blocks4_7: Mapped[float] = mapped_column(Float, nullable=False)

    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
