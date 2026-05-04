from __future__ import annotations
"""
Nudge Service

Orchestrates the full pipeline for one kinematic window:
  1. Fetch user profile (S_bias, motor baseline)
  2. Update W_fatigue via StateMonitor
  3. Classify via Rough Set engine (IS-based or heuristic fallback)
  4. Compute P via Risk Model
  5. Persist TelemetryWindow
  6. Return NudgeDecision + payloads
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import risk_model
from app.engine import rough_set
from app.engine.decision_rules import generate_rules
from app.middleware.state_monitor import state_registry
from app.models.db.telemetry_window import TelemetryWindow
from app.models.schemas.nudge import HardNudgePayload, SoftNudgePayload
from app.models.schemas.telemetry import KinematicWindow, NudgeDecision
from app.core.config import settings
from app.services.profile_service import get_user_for_session


# Number of cases in each phase. Cases 1..PHASE_MIDPOINT are phase 1,
# cases PHASE_MIDPOINT+1.. are phase 2.  Whether phase 1 is control or treatment
# depends on the session's nudge_order.
PHASE_MIDPOINT = 5

# Active case tracking: session_id → case_id
_active_case: dict[int, int | None] = {}

# Nudge-enabled cache: session_id → bool
# Updated each time a new case is loaded (phase may switch mid-session).
# The kinematic pipeline always runs — this only controls nudge delivery.
_nudge_enabled: dict[int, bool] = {}

# Crossover order cache: session_id → "control_first" | "treatment_first"
_nudge_order: dict[int, str] = {}


def set_active_case(session_id: int, case_id: int | None) -> None:
    _active_case[session_id] = case_id


def get_active_case(session_id: int) -> int | None:
    return _active_case.get(session_id)


def set_nudge_order(session_id: int, order: str) -> None:
    """Called at session start with the session's crossover order."""
    _nudge_order[session_id] = order


def compute_nudge_active(session_id: int, decisions_completed: int) -> bool:
    """
    Returns whether nudges should be active for the next case.

    Phase is determined by how many cases have already been decided:
      - decisions_completed < PHASE_MIDPOINT  → phase 1
      - decisions_completed >= PHASE_MIDPOINT → phase 2

    Which phase is control/treatment is set by nudge_order.
    """
    order = _nudge_order.get(session_id, "control_first")
    in_phase_one = decisions_completed < PHASE_MIDPOINT
    if order == "control_first":
        return not in_phase_one   # phase 1 = control (no nudge), phase 2 = treatment
    else:
        return in_phase_one       # phase 1 = treatment, phase 2 = control


def set_nudge_enabled(session_id: int, enabled: bool) -> None:
    _nudge_enabled[session_id] = enabled


def is_nudge_enabled(session_id: int) -> bool:
    return _nudge_enabled.get(session_id, False)


def clear_session_state(session_id: int) -> None:
    _active_case.pop(session_id, None)
    _nudge_enabled.pop(session_id, None)
    _nudge_order.pop(session_id, None)


async def process_kinematic_window(
    window: KinematicWindow,
    db: AsyncSession,
) -> NudgeDecision:
    """Full processing pipeline for one completed kinematic window."""

    # 1. User profile
    user = await get_user_for_session(window.session_id, db)
    # Per-dimension D-scores; fall back to population priors when IAT not yet completed
    s_bias_age    = user.s_bias_age    if user and user.s_bias_age    is not None else settings.s_bias_prior_age
    s_bias_gender = user.s_bias_gender if user and user.s_bias_gender is not None else settings.s_bias_prior_gender
    s_bias_race   = user.s_bias_race   if user and user.s_bias_race   is not None else settings.s_bias_prior_race
    # Composite for IS: max absolute score across dimensions
    s_bias        = max(abs(s_bias_age), abs(s_bias_gender), abs(s_bias_race))
    baseline    = user.d_score_baseline     if user and user.d_score_baseline     is not None else 1.0
    baseline_std = user.d_score_baseline_std if user and user.d_score_baseline_std is not None else 1.0

    # 2. Fatigue update
    monitor   = state_registry.get_or_create(window.session_id, baseline)
    w_fatigue = monitor.update(
        tortuosity=window.tortuosity,
        velocity_variance=window.velocity_variance,
        stutter_count=window.stutter_count,
    )

    # 3. Persist window first (need DB id before IS add)
    db_window = TelemetryWindow(
        session_id=window.session_id,
        window_start=window.window_start,
        window_end=window.window_end,
        point_count=window.point_count,
        tortuosity=window.tortuosity,
        mean_velocity=window.mean_velocity,
        velocity_variance=window.velocity_variance,
        acceleration_variance=window.acceleration_variance,
        stutter_count=window.stutter_count,
        tau_deviation=window.tau_deviation,
        time_on_task=window.time_on_task,
    )
    db.add(db_window)
    await db.flush()

    # 4. RST classification (adds window to IS with bootstrap label)
    case_id  = get_active_case(window.session_id)
    decision = rough_set.build_nudge_decision(
        window=window,
        window_id=db_window.id,
        w_fatigue=w_fatigue,
        s_bias=s_bias,
        case_id=case_id,
    )

    p = risk_model.compute_risk(w_fatigue, s_bias_age, s_bias_gender, s_bias_race)

    # 5. Persist classification result
    db_window.rs_classification = decision.classification
    db_window.risk_score        = p
    await db.commit()

    return decision


def build_hard_nudge_payload(decision: NudgeDecision) -> HardNudgePayload:
    ev = decision.evidence_summary
    rules = generate_rules(
        session_id=decision.session_id,
        window_id=decision.window_id,
        tau_deviation=ev.get("tau_deviation_sigma", 0.0),
        stutter_count=int(ev.get("stutter_count", 0)),
        w_fatigue=ev.get("fatigue_coefficient", 0.0),
        s_bias=ev.get("latent_bias_score", 0.0),
        classification=decision.classification,
    )
    return HardNudgePayload(
        window_id=decision.window_id,
        risk_score=decision.risk_score,
        evidence=rules,
    )


def build_soft_nudge_payload(
    decision: NudgeDecision,
    target_field_ids: list[str] | None = None,
) -> SoftNudgePayload:
    """
    Selects target fields based on the dominant feature driving classification.
    Defaults to the objective-data panel.
    """
    ev = decision.evidence_summary

    # Feature-driven field targeting
    if ev.get("tau_deviation_sigma", 0) > 2.0 or ev.get("stutter_count", 0) >= 2:
        targets = ["objective-data-panel", "vitals-section"]
    elif ev.get("fatigue_coefficient", 0) > 0.5:
        targets = ["objective-data-panel"]
    else:
        targets = target_field_ids or ["objective-data-panel"]

    return SoftNudgePayload(
        window_id=decision.window_id,
        risk_score=decision.risk_score,
        target_field_ids=targets,
        luminance_delta=min(0.1 + decision.risk_score * 0.5, 0.8),
    )
