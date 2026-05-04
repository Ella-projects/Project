from __future__ import annotations
"""
Analysis Service

Computes outcome metrics to assess whether the AUI made a measurable difference
in diagnostic error rates.

Design: within-subjects crossover. Each session is split at PHASE_MIDPOINT:
  - one phase runs with nudges active (treatment)
  - the other runs without nudges (control)
Order is counterbalanced by user_id parity.

Each CaseDecision records nudge_active so analysis requires no inference
about which phase it belonged to.

Primary question: Did adaptive nudges reduce errors on counter-stereotypical cases?

Key metrics:
  - delta_acc per phase: acc(counter_stereotypical) - acc(standard)
    A negative delta_acc = bias-driven errors. Narrowing it in treatment = AUI worked.
  - aui_effect_delta_acc: treatment.delta_acc - control.delta_acc (primary effect size)
  - nudge_effectiveness: accuracy when clinician changed decision after Hard Nudge
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.case import CaseDecision
from app.models.db.session import ClinicalSession


async def session_analysis(session_id: int, db: AsyncSession) -> dict:
    """
    Returns within-session analysis split by nudge phase.
    """
    sess_result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    dec_result = await db.execute(
        select(CaseDecision).where(CaseDecision.session_id == session_id)
    )
    decisions = dec_result.scalars().all()

    control_decs   = [d for d in decisions if not d.nudge_active]
    treatment_decs = [d for d in decisions if d.nudge_active]

    control   = _compute_phase_metrics(control_decs,   phase="control")
    treatment = _compute_phase_metrics(treatment_decs, phase="treatment")

    return {
        "session_id": session_id,
        "nudge_order": session.nudge_order,
        "total_decisions": len(decisions),
        "control": control,
        "treatment": treatment,
        "aui_effect_delta_acc": _safe_sub(
            treatment["delta_acc"], control["delta_acc"]
        ),
        "aui_effect_overall_acc": _safe_sub(
            treatment["overall_accuracy"], control["overall_accuracy"]
        ),
    }


async def user_analysis(user_id: int, db: AsyncSession) -> dict:
    """
    Aggregates across all sessions for a user.
    Each session contributes both control and treatment decisions.
    """
    sess_result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.user_id == user_id)
    )
    sessions = sess_result.scalars().all()
    if not sessions:
        raise ValueError(f"No sessions found for user {user_id}")

    session_ids = [s.id for s in sessions]

    dec_result = await db.execute(
        select(CaseDecision).where(CaseDecision.session_id.in_(session_ids))
    )
    all_decisions = dec_result.scalars().all()

    control_decs   = [d for d in all_decisions if not d.nudge_active]
    treatment_decs = [d for d in all_decisions if d.nudge_active]

    control   = _compute_phase_metrics(control_decs,   phase="control")
    treatment = _compute_phase_metrics(treatment_decs, phase="treatment")

    return {
        "user_id": user_id,
        "total_sessions": len(sessions),
        "total_decisions": len(all_decisions),
        "control": control,
        "treatment": treatment,
        # Primary effect: did nudges narrow the bias-driven accuracy gap?
        # Positive = treatment ΔAcc was better (less bias effect) than control ΔAcc
        "aui_effect_delta_acc": _safe_sub(
            treatment["delta_acc"], control["delta_acc"]
        ),
        # Secondary: did overall accuracy improve with nudges?
        "aui_effect_overall_acc": _safe_sub(
            treatment["overall_accuracy"], control["overall_accuracy"]
        ),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_phase_metrics(decisions: list[CaseDecision], phase: str) -> dict:
    if not decisions:
        return _empty_phase(phase)

    overall_accuracy = sum(d.is_correct for d in decisions) / len(decisions)

    cs_decs  = [d for d in decisions if d.is_counter_stereotypical]
    std_decs = [d for d in decisions if not d.is_counter_stereotypical]

    acc_cs  = sum(d.is_correct for d in cs_decs)  / len(cs_decs)  if cs_decs  else None
    acc_std = sum(d.is_correct for d in std_decs) / len(std_decs) if std_decs else None
    delta_acc = round(acc_cs - acc_std, 4) if (acc_cs is not None and acc_std is not None) else None

    nudge_decs   = [d for d in decisions if d.nudge_fired]
    changed_decs = [d for d in nudge_decs if d.nudge_outcome in ("changed_correct", "changed_incorrect")]
    unchanged_decs = [d for d in nudge_decs if d.nudge_outcome == "unchanged"]

    acc_after_change    = (
        sum(1 for d in changed_decs if d.nudge_outcome == "changed_correct") / len(changed_decs)
        if changed_decs else None
    )
    acc_after_unchanged = (
        sum(d.is_correct for d in unchanged_decs) / len(unchanged_decs)
        if unchanged_decs else None
    )
    rule_adherence = len(changed_decs) / len(nudge_decs) if nudge_decs else None

    return {
        "phase": phase,
        "total_decisions": len(decisions),
        "overall_accuracy": round(overall_accuracy, 4),
        "accuracy_standard": round(acc_std, 4) if acc_std is not None else None,
        "accuracy_counter_stereotypical": round(acc_cs, 4) if acc_cs is not None else None,
        "delta_acc": delta_acc,
        "nudge_fires": len(nudge_decs),
        "rule_adherence_rate": round(rule_adherence, 4) if rule_adherence is not None else None,
        "accuracy_after_nudge_changed": round(acc_after_change, 4) if acc_after_change is not None else None,
        "accuracy_after_nudge_unchanged": round(acc_after_unchanged, 4) if acc_after_unchanged is not None else None,
    }


def _empty_phase(phase: str) -> dict:
    return {
        "phase": phase,
        "total_decisions": 0,
        "overall_accuracy": None,
        "accuracy_standard": None,
        "accuracy_counter_stereotypical": None,
        "delta_acc": None,
        "nudge_fires": 0,
        "rule_adherence_rate": None,
        "accuracy_after_nudge_changed": None,
        "accuracy_after_nudge_unchanged": None,
    }


def _safe_sub(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 4)
