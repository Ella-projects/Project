from __future__ import annotations
import math
from datetime import datetime, timezone

import pytest

from app.models.schemas.telemetry import MousePoint


# ── Mouse point factories ──────────────────────────────────────────────────────

def straight_line(n: int = 20, t_start: float = 0.0, dt: float = 50.0) -> list[MousePoint]:
    """Horizontal straight line: tortuosity should equal exactly 1.0."""
    return [MousePoint(x=float(i * 10), y=0.0, t=t_start + i * dt) for i in range(n)]


def right_angle(t_start: float = 0.0, dt: float = 50.0) -> list[MousePoint]:
    """
    Path: (0,0) → (100,0) → (100,100).
    path_length = 200, displacement = 100√2 ≈ 141.42, τ ≈ 1.414.
    """
    leg1 = [MousePoint(x=float(i * 10), y=0.0, t=t_start + i * dt) for i in range(11)]
    leg2 = [MousePoint(x=100.0, y=float(i * 10), t=t_start + (11 + i) * dt) for i in range(1, 11)]
    return leg1 + leg2


def stationary(n: int = 20, t_start: float = 0.0, dt: float = 50.0) -> list[MousePoint]:
    """All points at the same location — displacement ≈ 0."""
    return [MousePoint(x=50.0, y=50.0, t=t_start + i * dt) for i in range(n)]


def high_tortuosity(t_start: float = 0.0, dt: float = 50.0) -> list[MousePoint]:
    """Zigzag path with high tortuosity."""
    points = []
    for i in range(30):
        x = float(i * 5)
        y = 50.0 if i % 2 == 0 else -50.0
        points.append(MousePoint(x=x, y=y, t=t_start + i * dt))
    return points


# ── IAT trial factory ──────────────────────────────────────────────────────────

def make_trial(
    block: int,
    rt: int,
    correct: bool = True,
    practice: bool = False,
) -> dict:
    return {
        "block_number": block,
        "reaction_time_ms": rt,
        "is_correct": correct,
        "is_practice": practice,
    }
