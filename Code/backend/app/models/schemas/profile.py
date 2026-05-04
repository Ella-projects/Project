from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id:                   int
    username:             str
    s_bias_age:           Optional[float]
    s_bias_gender:        Optional[float]
    s_bias_race:          Optional[float]
    d_score_baseline:     Optional[float]
    d_score_baseline_std: Optional[float]
    created_at:           datetime

    class Config:
        from_attributes = True


class BaselineCalibrationResult(BaseModel):
    """Result after computing motor baseline from a calibration session."""

    user_id: int
    d_score_baseline: float
    d_score_baseline_std: float
    window_count: int


class IATSummary(BaseModel):
    """Public-facing summary of one IAT D-score (one bias dimension)."""

    user_id:        int
    bias_type:      str            # "age" | "gender" | "race"
    d_score:        float = Field(..., description="Greenwald D-score in [-2, 2]")
    interpretation: str            # e.g. "slight", "moderate", "strong" bias
    completed_at:   datetime
