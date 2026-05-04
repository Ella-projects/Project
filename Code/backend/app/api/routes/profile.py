from __future__ import annotations
"""
User Profile Routes

GET  /profile/{user_id}           — Fetch user profile
POST /profile/{user_id}/baseline  — Submit calibration tortuosity values
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas.profile import BaselineCalibrationResult, UserProfile
from app.services.profile_service import compute_and_store_baseline, get_user_by_id
from pydantic import BaseModel

router = APIRouter(prefix="/profile", tags=["profile"])


class BaselineSubmission(BaseModel):
    tortuosity_values: list[float]


@router.get("/{user_id}", response_model=UserProfile)
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/{user_id}/baseline", response_model=BaselineCalibrationResult)
async def submit_baseline(
    user_id: int,
    submission: BaselineSubmission,
    db: AsyncSession = Depends(get_db),
):
    """
    Stores motor baseline from a calibration session.
    Called after a neutral-task warm-up with no cognitive load.
    """
    if len(submission.tortuosity_values) < 5:
        raise HTTPException(
            status_code=422,
            detail="Minimum 5 tortuosity values required for baseline.",
        )
    return await compute_and_store_baseline(user_id, submission.tortuosity_values, db)
