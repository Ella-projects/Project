from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TriageCaseOut(BaseModel):
    id: int
    patient_label: str
    chief_complaint: str
    vitals: dict[str, str]
    objective_findings: list[str]
    correct_decision: str
    is_counter_stereotypical: bool
    nudge_active: bool = False  # whether nudges are enabled for this case

    class Config:
        from_attributes = True


class DecisionSubmission(BaseModel):
    session_id: int
    case_id: int
    decision: str
    window_id: Optional[int] = None
    # Set by the frontend when a Hard Nudge intercepted Submit
    nudge_fired: bool = False
    pre_nudge_decision: Optional[str] = None  # original decision before nudge


class DecisionResult(BaseModel):
    is_correct: bool
    correct_decision: str
    delta_acc: float  # running ΔAcc for this session
