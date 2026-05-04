from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MousePoint(BaseModel):
    x: float
    y: float
    t: float = Field(..., description="Unix timestamp in milliseconds")


class TelemetryFrame(BaseModel):
    """Batch of mouse points sent over WebSocket from the client."""

    session_id: int
    points: list[MousePoint]


class KinematicWindow(BaseModel):
    """Processed output from the kinematic processor for one 5-second window."""

    session_id: int
    window_start: datetime
    window_end: datetime
    point_count: int

    tortuosity: float
    mean_velocity: float
    velocity_variance: float
    acceleration_variance: float
    stutter_count: int
    tau_deviation: float
    time_on_task: float


class NudgeDecision(BaseModel):
    """Output from the Rough Set engine — what action the UI should take."""

    session_id: int
    window_id: int
    classification: str  # "positive_region" | "boundary_region" | "negative_region"
    risk_score: float
    nudge_type: Optional[str]  # "hard" | "soft" | None
    evidence_summary: dict  # Human-readable rule firing details
