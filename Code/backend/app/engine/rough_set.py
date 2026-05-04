from __future__ import annotations
"""
Rough Set Logic Engine

Classification pipeline for one TelemetryWindow:

  1. Add the window to the session InformationSystem (IS) with a bootstrap label.
  2. If IS.size ≥ MIN_OBJECTS_FOR_RST  → use RST-based classification.
  3. Otherwise                          → fall back to the weighted heuristic.
  4. Map region → nudge type.
  5. Return a NudgeDecision.

The IS accumulates labelled objects across the session.  Labels are
retrospectively corrected by case_service when a triage decision outcome
is known, progressively improving classification accuracy.
"""

from dataclasses import dataclass

import numpy as np

from app.core.config import settings
from app.engine.information_system import (
    ATTRIBUTES,
    InformationSystem,
    LabeledObject,
    bootstrap_label,
    discretize,
    is_registry,
)
from app.models.schemas.telemetry import KinematicWindow, NudgeDecision


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic fallback (used when IS has < MIN_OBJECTS_FOR_RST rows)
# ─────────────────────────────────────────────────────────────────────────────

def _heuristic_score(attrs: dict[str, float]) -> float:
    """
    Weighted membership score ∈ [0, 1] for the high_risk concept.
    Used as a bootstrap classifier before the IS has sufficient data.

    Weights reflect theoretical importance per the AUI specification.
    TODO: calibrate weights from empirical session-outcome data.
    """
    tau_score     = np.clip(attrs["tau_deviation"]         / 3.0,   0.0, 1.0)
    stutter_score = np.clip(attrs["stutter_count"]         / 3.0,   0.0, 1.0)
    vel_score     = np.clip(attrs["velocity_variance"]     / 500.0, 0.0, 1.0)
    accel_score   = np.clip(attrs["acceleration_variance"] / 200.0, 0.0, 1.0)
    fatigue_score = float(attrs["w_fatigue"])
    bias_score    = np.clip(abs(attrs["s_bias"])           / 2.0,   0.0, 1.0)

    return float(
        0.30 * tau_score
        + 0.25 * stutter_score
        + 0.10 * vel_score
        + 0.10 * accel_score
        + 0.15 * fatigue_score
        + 0.10 * bias_score
    )


def _heuristic_classify(attrs: dict[str, float]) -> tuple[str, float]:
    score = _heuristic_score(attrs)
    if score >= settings.lower_approx_threshold:
        return "positive_region", score
    elif score >= settings.boundary_region_threshold:
        return "boundary_region", score
    else:
        return "negative_region", score


# ─────────────────────────────────────────────────────────────────────────────
# Main classification entry point
# ─────────────────────────────────────────────────────────────────────────────

def classify_window(
    attrs: dict[str, float],
    session_id: int,
    window_id: int,
    case_id: int | None,
) -> tuple[str, float, bool]:
    """
    Classifies a kinematic window.

    Steps:
      1. Discretize attrs → AttrVector
      2. Bootstrap-label the object
      3. Add to IS
      4. Classify: RST if IS is mature, heuristic otherwise
      5. Return (region, certainty, used_rst)

    Parameters
    ----------
    attrs      : raw kinematic + context attributes
    session_id : session owning this window
    window_id  : DB id of the persisted TelemetryWindow
    case_id    : active triage case when this window was recorded (may be None
                 during calibration or between cases)
    """
    vec   = discretize(attrs)
    label = bootstrap_label(attrs)

    obj = LabeledObject(
        window_id=window_id,
        case_id=case_id,
        attrs=attrs,
        discretized=vec,
        label=label,
        label_source="bootstrap",
    )

    is_sys: InformationSystem = is_registry.get_or_create(session_id)
    is_sys.add_object(obj)

    region, certainty = is_sys.classify(vec)

    if region == "insufficient_data":
        region, certainty = _heuristic_classify(attrs)
        return region, certainty, False

    return region, certainty, True


# ─────────────────────────────────────────────────────────────────────────────
# NudgeDecision builder
# ─────────────────────────────────────────────────────────────────────────────

def build_nudge_decision(
    window: KinematicWindow,
    window_id: int,
    w_fatigue: float,
    s_bias: float,
    case_id: int | None = None,
) -> NudgeDecision:
    """
    Top-level entry point called by NudgeService.
    Builds the attribute dict, classifies, and returns a NudgeDecision.
    """
    attrs = {
        "tortuosity":            window.tortuosity,
        "tau_deviation":         window.tau_deviation,
        "stutter_count":         float(window.stutter_count),
        "velocity_variance":     window.velocity_variance,
        "acceleration_variance": window.acceleration_variance,
        "time_on_task":          window.time_on_task,
        "w_fatigue":             w_fatigue,
        "s_bias":                s_bias,
    }

    region, certainty, used_rst = classify_window(
        attrs=attrs,
        session_id=window.session_id,
        window_id=window_id,
        case_id=case_id,
    )

    nudge_type: str | None
    if region == "positive_region":
        nudge_type = "hard"
    elif region == "boundary_region":
        nudge_type = "soft"
    else:
        nudge_type = None

    return NudgeDecision(
        session_id=window.session_id,
        window_id=window_id,
        classification=region,
        risk_score=round(certainty, 4),
        nudge_type=nudge_type,
        evidence_summary={
            "certainty":            round(certainty, 3),
            "classifier":          "rst" if used_rst else "heuristic",
            "tortuosity":          round(window.tortuosity, 3),
            "tau_deviation_sigma": round(window.tau_deviation, 2),
            "stutter_count":       window.stutter_count,
            "fatigue_coefficient": round(w_fatigue, 3),
            "latent_bias_score":   round(s_bias, 3),
        },
    )
