from __future__ import annotations
"""
Nudge Acknowledgement Route

POST /nudge/acknowledge — Client confirms a Hard Nudge, recording decision delta.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.models.db.session import ClinicalSession
from app.models.schemas.nudge import NudgeAcknowledgement

router = APIRouter(prefix="/nudge", tags=["nudge"])


@router.post("/acknowledge", status_code=200)
async def acknowledge_nudge(
    ack: NudgeAcknowledgement,
    db: AsyncSession = Depends(get_db),
):
    """
    Records whether the clinician changed their decision after a Hard Nudge.
    Updates the session's rule_adherence_rate metric.
    """
    decision_changed = ack.original_decision != ack.final_decision

    # Fetch current session stats
    result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.id == ack.session_id)
    )
    session = result.scalar_one_or_none()

    if session:
        session.hard_nudge_count    = (session.hard_nudge_count    or 0) + 1
        session.hard_nudge_accepted = (session.hard_nudge_accepted or 0) + (1 if decision_changed else 0)
        session.rule_adherence_rate = round(
            session.hard_nudge_accepted / session.hard_nudge_count, 4
        )
        await db.commit()

    return {
        "acknowledged": True,
        "decision_changed": decision_changed,
        "session_id": ack.session_id,
    }
