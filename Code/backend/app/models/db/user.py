from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """Stores clinician identity and latent bias profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Latent Bias Repository — IAT D-scores per dimension, range [-2, 2]
    s_bias_age:    Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    s_bias_gender: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    s_bias_race:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Motor Variance Baseline — mean tortuosity τ under no-load conditions
    d_score_baseline: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Baseline tortuosity standard deviation for adaptive thresholding
    d_score_baseline_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
