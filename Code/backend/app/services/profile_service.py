from __future__ import annotations
"""
Profile Service

Manages reading and updating the user's latent bias repository (S_bias)
and motor variance baselines (D-Score Baseline).
"""

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.session import ClinicalSession
from app.models.db.user import User
from app.models.schemas.profile import BaselineCalibrationResult


async def get_user_by_id(user_id: int, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_for_session(session_id: int, db: AsyncSession) -> User | None:
    """Resolves the user associated with a clinical session."""
    result = await db.execute(
        select(User)
        .join(ClinicalSession, ClinicalSession.user_id == User.id)
        .where(ClinicalSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def update_s_bias(
    user_id: int,
    d_score: float,
    bias_type: str,
    db: AsyncSession,
) -> None:
    """
    Stores the IAT D-score for the given bias dimension on the user profile.
    bias_type must be one of: "age", "gender", "race".
    Called after each completed IAT administration.
    """
    if bias_type not in ("age", "gender", "race"):
        raise ValueError(f"Unknown bias_type: {bias_type!r}")
    user = await get_user_by_id(user_id, db)
    if user:
        setattr(user, f"s_bias_{bias_type}", d_score)
        await db.commit()


async def compute_and_store_baseline(
    user_id: int,
    tortuosity_values: list[float],
    db: AsyncSession,
) -> BaselineCalibrationResult:
    """
    Computes motor baseline statistics from a calibration session
    (user moves the mouse through a neutral task with no cognitive load).

    Stores d_score_baseline (mean τ) and d_score_baseline_std (σ τ) on the user.
    """
    arr = np.array(tortuosity_values, dtype=float)
    baseline_mean = float(np.mean(arr))
    baseline_std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.1

    user = await get_user_by_id(user_id, db)
    if user:
        user.d_score_baseline = baseline_mean
        user.d_score_baseline_std = baseline_std
        await db.commit()

    return BaselineCalibrationResult(
        user_id=user_id,
        d_score_baseline=baseline_mean,
        d_score_baseline_std=baseline_std,
        window_count=len(tortuosity_values),
    )
