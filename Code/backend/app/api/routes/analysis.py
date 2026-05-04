from __future__ import annotations
"""
Analysis Routes

GET /analysis/session/{id}  — AUI effect metrics for one session
GET /analysis/user/{id}     — Aggregated metrics across all sessions for a user,
                              split by condition (control vs treatment)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analysis_service import session_analysis, user_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/session/{session_id}")
async def get_session_analysis(session_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns accuracy metrics and nudge effectiveness for a single session.
    Use this at the end of a session to show the clinician their performance summary.
    """
    try:
        return await session_analysis(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/user/{user_id}")
async def get_user_analysis(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Aggregates all sessions for a user split by condition.

    Key fields:
      - aui_effect_delta_acc:    treatment ΔAcc − control ΔAcc
                                 Positive = AUI narrowed the bias-driven accuracy gap
      - aui_effect_overall_acc:  treatment overall accuracy − control overall accuracy
      - control.delta_acc:       ΔAcc in sessions without nudges
      - treatment.delta_acc:     ΔAcc in sessions with nudges
    """
    try:
        return await user_analysis(user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
