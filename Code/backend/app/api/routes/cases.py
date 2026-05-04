from __future__ import annotations
from sqlalchemy import select, func
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db.case import CaseDecision
from app.models.db.session import ClinicalSession
from app.models.schemas.case import DecisionResult, DecisionSubmission, TriageCaseOut
from app.services.case_service import get_next_case, serialize_case, submit_decision
from app.services.nudge_service import (
    compute_nudge_active,
    is_nudge_enabled,
    set_active_case,
    set_nudge_enabled,
    set_nudge_order,
)

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/next/{session_id}", response_model=TriageCaseOut)
async def next_case(session_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns the next unseen triage case and switches the nudge phase if the
    midpoint has been reached (within-subjects crossover).
    """
    case = await get_next_case(session_id, db)
    if not case:
        set_active_case(session_id, None)
        raise HTTPException(status_code=404, detail="No more cases")

    # Re-warm nudge_order cache from DB in case of server restart / hot-reload
    session_result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.id == session_id)
    )
    db_session = session_result.scalar_one_or_none()
    if db_session:
        set_nudge_order(session_id, db_session.nudge_order)

    # Count decisions already submitted this session to determine phase
    count_result = await db.execute(
        select(func.count()).select_from(CaseDecision)
        .where(CaseDecision.session_id == session_id)
    )
    decisions_completed = count_result.scalar_one()

    nudge_active = compute_nudge_active(session_id, decisions_completed)
    set_nudge_enabled(session_id, nudge_active)
    set_active_case(session_id, case.id)

    return serialize_case(case, nudge_active=nudge_active)


@router.post("/decision", response_model=DecisionResult)
async def record_decision(
    submission: DecisionSubmission,
    db: AsyncSession = Depends(get_db),
):
    """Records the clinician's decision and returns correctness + updated ΔAcc."""
    # Capture the current nudge phase before the decision is persisted
    nudge_active = is_nudge_enabled(submission.session_id)

    try:
        is_correct, correct_decision, delta_acc = await submit_decision(
            session_id=submission.session_id,
            case_id=submission.case_id,
            decision=submission.decision,
            window_id=submission.window_id,
            db=db,
            nudge_active=nudge_active,
            nudge_fired=submission.nudge_fired,
            pre_nudge_decision=submission.pre_nudge_decision,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return DecisionResult(
        is_correct=is_correct,
        correct_decision=correct_decision,
        delta_acc=delta_acc,
    )
