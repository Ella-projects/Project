from __future__ import annotations
from pydantic import BaseModel, Field


class HardNudgePayload(BaseModel):
    """Sent to client to trigger a modal intercept on Submit."""

    nudge_type: str = "hard"
    window_id: int
    risk_score: float
    evidence: list[str]  # Bullet-point reasons shown to the clinician
    requires_confirmation: bool = True


class SoftNudgePayload(BaseModel):
    """Sent to client to trigger an ambient saliency shift."""

    nudge_type: str = "soft"
    window_id: int
    risk_score: float
    target_field_ids: list[str]  # DOM IDs of fields to highlight
    luminance_delta: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Luminance modulation intensity [0–1]",
    )
    duration_ms: int = 3000


class NudgeAcknowledgement(BaseModel):
    """Client confirms a Hard Nudge — records whether the decision changed."""

    window_id: int
    session_id: int
    original_decision: str
    final_decision: str
    confirmed_at: str  # ISO timestamp
