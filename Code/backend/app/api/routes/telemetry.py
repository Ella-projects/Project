from __future__ import annotations
"""
WebSocket endpoint for real-time mouse telemetry.

Flow per message:
  client → raw MousePoints → WindowBuffer → KinematicProcessor
  → NudgeService → NudgeDecision → client (same socket)
"""

import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.kinematic_processor import process_window
from app.middleware.windowing import window_manager
from app.models.schemas.telemetry import MousePoint, TelemetryFrame
from app.services.nudge_service import (
    build_hard_nudge_payload,
    build_soft_nudge_payload,
    is_nudge_enabled,
    process_kinematic_window,
)
from app.services.profile_service import get_user_for_session

router = APIRouter(prefix="/ws", tags=["telemetry"])
logger = logging.getLogger(__name__)


@router.websocket("/telemetry/{session_id}")
async def telemetry_socket(
    websocket: WebSocket,
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a stream of TelemetryFrame JSON messages.
    Responds with NudgeDecision messages when a completed window is classified.
    """
    await websocket.accept()
    logger.info("WebSocket opened for session %d", session_id)

    buffer = window_manager.get(session_id)

    try:
        # Fetch baseline once per connection
        user = await get_user_for_session(session_id, db)
        baseline_mean = user.d_score_baseline if user else None
        baseline_std = user.d_score_baseline_std if user else None

        while True:
            raw = await websocket.receive_text()
            frame = TelemetryFrame.model_validate_json(raw)

            completed_windows = buffer.ingest(frame.points)

            for window_points in completed_windows:
                kinematic = process_window(
                    points=window_points,
                    baseline_mean=baseline_mean,
                    baseline_std=baseline_std,
                    session_id=session_id,
                )

                decision = await process_kinematic_window(kinematic, db)

                # In control sessions the pipeline runs in full but nudges are suppressed
                nudges_active = is_nudge_enabled(session_id)

                if nudges_active and decision.nudge_type == "hard":
                    payload = build_hard_nudge_payload(decision)
                    await websocket.send_text(
                        json.dumps({"type": "hard_nudge", "data": payload.model_dump()})
                    )

                elif nudges_active and decision.nudge_type == "soft":
                    payload = build_soft_nudge_payload(decision)
                    await websocket.send_text(
                        json.dumps({"type": "soft_nudge", "data": payload.model_dump()})
                    )

                else:
                    # No nudge (or control condition) — lightweight ack for debugging
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "window_clear",
                                "window_id": decision.window_id,
                                "risk_score": decision.risk_score,
                                "nudge_suppressed": not nudges_active and decision.nudge_type != "none",
                            }
                        )
                    )

    except WebSocketDisconnect:
        logger.info("WebSocket closed for session %d", session_id)
        window_manager.remove(session_id)
    except Exception as exc:
        logger.exception("Telemetry socket error for session %d: %s", session_id, exc)
        await websocket.close(code=1011)
