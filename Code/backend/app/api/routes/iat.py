from __future__ import annotations
"""
IAT Administration Routes

GET  /iat/blocks         — Returns the full block/stimulus sequence for a session
POST /iat/response       — Records a single trial response
POST /iat/complete       — Finalizes the IAT, computes D-score, stores S_bias
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.db.iat_result import IATResult, IATTrial
from app.models.schemas.profile import IATSummary
from app.services.iat_service import (
    build_block_specs,
    compute_d_score,
    generate_stimuli_for_block,
    interpret_d_score,
)
from app.services.profile_service import update_s_bias

router = APIRouter(prefix="/iat", tags=["iat"])


class BlocksResponse(BaseModel):
    session_id: int
    blocks: list[dict]  # list of {block_number, is_practice, stimuli: [...]}


class TrialResponse(BaseModel):
    session_id:        int
    bias_type:         str = "age"   # "age" | "gender" | "race"
    block_number:      int
    trial_number:      int
    stimulus_word:     str
    stimulus_category: str
    correct_key:       str
    response_key:      str
    reaction_time_ms:  int
    is_correct:        bool
    presented_at:      str  # ISO timestamp


class CompleteRequest(BaseModel):
    session_id: int
    user_id:    int
    bias_type:  str = "age"   # "age" | "gender" | "race"


@router.get("/blocks/{session_id}", response_model=BlocksResponse)
async def get_iat_blocks(session_id: int, bias_type: str = "age"):
    """
    Generates the complete IAT stimulus sequence for the session.
    Called once per IAT; bias_type selects the demographic pair:
      "age" → Elderly/Young, "gender" → Male/Female, "race" → White/Black.
    The frontend calls this three times (once per bias_type) before clinical cases begin.
    """
    specs = build_block_specs(
        practice_count=settings.iat_practice_trial_count,
        test_count_short=settings.iat_trial_count // 4,
        test_count_long=settings.iat_trial_count // 2,
        bias_type=bias_type,
    )

    blocks = []
    for spec in specs:
        stimuli = generate_stimuli_for_block(spec)
        blocks.append(
            {
                "block_number": spec.block_number,
                "is_practice": spec.is_practice,
                "left_label": ", ".join(spec.left_categories),
                "right_label": ", ".join(spec.right_categories),
                "stimuli": [
                    {
                        "trial_number": s.trial_number,
                        "word": s.word,
                        "category": s.category,
                        "correct_key": s.correct_key,
                    }
                    for s in stimuli
                ],
            }
        )

    return BlocksResponse(session_id=session_id, blocks=blocks)


@router.post("/response", status_code=201)
async def record_trial_response(
    response: TrialResponse,
    db: AsyncSession = Depends(get_db),
):
    """Records a single IAT trial response."""
    trial = IATTrial(
        session_id=response.session_id,
        bias_type=response.bias_type,
        block_number=response.block_number,
        trial_number=response.trial_number,
        is_practice=False,
        stimulus_word=response.stimulus_word,
        stimulus_category=response.stimulus_category,
        correct_key=response.correct_key,
        response_key=response.response_key,
        reaction_time_ms=response.reaction_time_ms,
        is_correct=response.is_correct,
        presented_at=datetime.fromisoformat(response.presented_at),
    )
    db.add(trial)
    await db.commit()
    return {"status": "recorded"}


@router.post("/complete", response_model=IATSummary)
async def complete_iat(
    request: CompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Finalizes the IAT administration:
    1. Loads all trials for the session
    2. Computes D-score
    3. Persists IATResult
    4. Updates user S_bias
    """
    from sqlalchemy import select
    from app.models.db.iat_result import IATTrial

    result = await db.execute(
        select(IATTrial).where(
            IATTrial.session_id == request.session_id,
            IATTrial.bias_type  == request.bias_type,
        )
    )
    trials = result.scalars().all()

    if not trials:
        raise HTTPException(
            status_code=404,
            detail=f"No {request.bias_type} IAT trials found for session {request.session_id}",
        )

    trial_dicts = [
        {
            "block_number": t.block_number,
            "reaction_time_ms": t.reaction_time_ms or 9999,
            "is_correct": t.is_correct if t.is_correct is not None else False,
            "is_practice": t.is_practice,
        }
        for t in trials
    ]

    scores = compute_d_score(trial_dicts)

    iat_result = IATResult(
        user_id=request.user_id,
        session_id=request.session_id,
        bias_type=request.bias_type,
        **scores,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(iat_result)
    await db.flush()

    await update_s_bias(request.user_id, scores["d_score"], request.bias_type, db)
    await db.commit()

    return IATSummary(
        user_id=request.user_id,
        bias_type=request.bias_type,
        d_score=scores["d_score"],
        interpretation=interpret_d_score(scores["d_score"]),
        completed_at=iat_result.completed_at,
    )
