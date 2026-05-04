from __future__ import annotations
"""
Session Management Routes

POST /session/start  — Opens a new ClinicalSession for a user
POST /session/end    — Closes the session and persists final metrics
GET  /session/{id}   — Fetch session status and metrics
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engine.information_system import is_registry
from app.middleware.state_monitor import state_registry
from app.middleware.windowing import window_manager
from app.models.db.session import ClinicalSession
from app.services.nudge_service import set_nudge_order, clear_session_state

router = APIRouter(prefix="/session", tags=["session"])


class StartRequest(BaseModel):
    user_id: int


class SessionOut(BaseModel):
    id: int
    user_id: int
    nudge_order: str
    w_fatigue: float
    delta_acc: Optional[float]
    rule_adherence_rate: Optional[float]
    started_at: datetime
    ended_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/start", response_model=SessionOut, status_code=201)
async def start_session(
    request: StartRequest,
    db: AsyncSession = Depends(get_db),
):
    # Counterbalanced by user_id parity so the two groups are even.
    # Even user IDs see control phase first; odd user IDs see treatment phase first.
    nudge_order = "control_first" if request.user_id % 2 == 0 else "treatment_first"

    session = ClinicalSession(
        user_id=request.user_id,
        nudge_order=nudge_order,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Cache crossover order so the cases route can compute phase without a DB hit
    set_nudge_order(session.id, nudge_order)

    return session


@router.post("/end/{session_id}", response_model=SessionOut)
async def end_session(session_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    monitor = state_registry.get_or_create(session_id)
    session.w_fatigue = monitor.w_fatigue
    session.ended_at = datetime.now(timezone.utc)
    session.is_active = False

    await db.commit()

    # Cleanup in-memory state
    state_registry.remove(session_id)
    window_manager.remove(session_id)
    is_registry.remove(session_id)
    clear_session_state(session_id)

    return session


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ClinicalSession).where(ClinicalSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Re-warm the in-memory cache (e.g. after a server restart)
    set_nudge_order(session_id, session.nudge_order)
    return session
