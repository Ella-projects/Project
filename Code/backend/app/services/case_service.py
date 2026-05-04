from __future__ import annotations
import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.information_system import is_registry
from app.models.db.case import CaseDecision, TriageCase
from app.models.db.session import ClinicalSession
from app.models.schemas.case import TriageCaseOut


async def get_next_case(session_id: int, db: AsyncSession) -> TriageCase | None:
    """
    Returns the next case not yet decided in this session.
    Counter-stereotypical cases are distributed evenly throughout the queue.
    """
    decided = select(CaseDecision.case_id).where(CaseDecision.session_id == session_id)
    result = await db.execute(
        select(TriageCase)
        .where(TriageCase.id.not_in(decided))
        .order_by(TriageCase.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


def serialize_case(case: TriageCase, nudge_active: bool = False) -> TriageCaseOut:
    return TriageCaseOut(
        id=case.id,
        patient_label=case.patient_label,
        chief_complaint=case.chief_complaint,
        vitals=json.loads(case.vitals_json),
        objective_findings=case.objective_findings.split("\n"),
        correct_decision=case.correct_decision,
        is_counter_stereotypical=case.is_counter_stereotypical,
        nudge_active=nudge_active,
    )


async def submit_decision(
    session_id: int,
    case_id: int,
    decision: str,
    window_id: int | None,
    db: AsyncSession,
    nudge_active: bool = False,
    nudge_fired: bool = False,
    pre_nudge_decision: str | None = None,
) -> tuple[bool, str, float]:
    """
    Records a decision, computes whether it is correct, and updates ΔAcc.

    Returns (is_correct, correct_decision, delta_acc).

    ΔAcc = accuracy_on_counter_stereotypical - accuracy_on_standard
    A negative ΔAcc indicates bias-driven errors on counter-stereotypical cases.
    """
    case_result = await db.execute(select(TriageCase).where(TriageCase.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    is_correct = decision.lower() == case.correct_decision.lower()

    # Retrospectively relabel IS windows recorded during this case
    is_sys = is_registry.get_or_create(session_id)
    is_sys.update_labels_for_case(case_id, is_correct, source="outcome")

    # Determine nudge outcome
    nudge_outcome: str | None = None
    if nudge_fired and pre_nudge_decision is not None:
        decision_changed = decision.lower() != pre_nudge_decision.lower()
        if decision_changed:
            nudge_outcome = "changed_correct" if is_correct else "changed_incorrect"
        else:
            nudge_outcome = "unchanged"

    record = CaseDecision(
        session_id=session_id,
        case_id=case_id,
        decision=decision,
        is_correct=is_correct,
        is_counter_stereotypical=case.is_counter_stereotypical,
        window_id=window_id,
        nudge_active=nudge_active,
        nudge_fired=nudge_fired,
        pre_nudge_decision=pre_nudge_decision,
        nudge_outcome=nudge_outcome,
    )
    db.add(record)
    await db.flush()

    delta_acc = await _compute_delta_acc(session_id, db)

    # Persist delta_acc onto the session
    session_result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if session:
        session.delta_acc = delta_acc

    await db.commit()
    return is_correct, case.correct_decision, delta_acc


async def _compute_delta_acc(session_id: int, db: AsyncSession) -> float:
    """
    ΔAcc = acc(counter_stereotypical) - acc(standard)

    Returns 0.0 if insufficient data on either side.
    """
    result = await db.execute(
        select(CaseDecision.is_counter_stereotypical, CaseDecision.is_correct)
        .where(CaseDecision.session_id == session_id)
    )
    rows = result.all()

    buckets: dict[bool, list[bool]] = {True: [], False: []}
    for is_cs, is_correct in rows:
        buckets[is_cs].append(is_correct)

    if not buckets[True] or not buckets[False]:
        return 0.0

    acc_cs = sum(buckets[True]) / len(buckets[True])
    acc_std = sum(buckets[False]) / len(buckets[False])
    return round(acc_cs - acc_std, 4)
