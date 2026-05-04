from __future__ import annotations
"""
Kinematic Processing Layer — Tortuosity (τ) Engine

Transforms a raw list of (x, y, t) points into the kinematic feature vector
used by the Rough Set engine.

Key output: tortuosity τ = actual_path_length / straight_line_displacement

Stutters are defined as local τ spikes that exceed the user's baseline by ≥ α std devs.
"""

import math
from datetime import datetime, timezone

import numpy as np

from app.models.schemas.telemetry import KinematicWindow, MousePoint


def _euclidean(a: MousePoint, b: MousePoint) -> float:
    return math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)


def compute_tortuosity(points: list[MousePoint]) -> float:
    """
    τ = Σ segment lengths / straight-line displacement(start → end).
    Returns 1.0 (minimum) when the path is perfectly straight.
    Returns a large value for highly curved / backtracking paths.
    """
    if len(points) < 2:
        return 1.0

    path_length = sum(_euclidean(points[i], points[i + 1]) for i in range(len(points) - 1))
    displacement = _euclidean(points[0], points[-1])

    if displacement < 1e-6:
        # Cursor barely moved — treat as maximum tortuosity sentinel
        return float(path_length) if path_length > 0 else 1.0

    return path_length / displacement


def compute_velocities(points: list[MousePoint]) -> np.ndarray:
    """Returns per-segment speed in pixels/ms."""
    velocities = []
    for i in range(len(points) - 1):
        dt = points[i + 1].t - points[i].t
        if dt <= 0:
            continue
        dist = _euclidean(points[i], points[i + 1])
        velocities.append(dist / dt)
    return np.array(velocities, dtype=float)


def detect_stutters(
    points: list[MousePoint],
    baseline_mean: float,
    baseline_std: float,
    alpha: float = 2.0,
) -> int:
    """
    Count micro-windows within the window where local τ exceeds
    (baseline_mean + alpha * baseline_std).

    TODO: sub-window granularity configurable; currently uses thirds of the window.
    """
    if baseline_std < 1e-6 or len(points) < 6:
        return 0

    threshold = baseline_mean + alpha * baseline_std
    chunk_size = len(points) // 3
    stutter_count = 0

    for i in range(3):
        chunk = points[i * chunk_size : (i + 1) * chunk_size]
        if len(chunk) >= 2:
            local_tau = compute_tortuosity(chunk)
            if local_tau > threshold:
                stutter_count += 1

    return stutter_count


def process_window(
    points: list[MousePoint],
    baseline_mean: float | None,
    baseline_std: float | None,
    session_id: int,
) -> KinematicWindow:
    """
    Entry point: convert raw points into a KinematicWindow feature vector.

    If the user has no established baseline (first session), tau_deviation is 0.0
    and stutter detection is skipped.
    """
    tau = compute_tortuosity(points)
    velocities = compute_velocities(points)

    mean_v = float(np.mean(velocities)) if len(velocities) > 0 else 0.0
    var_v = float(np.var(velocities)) if len(velocities) > 0 else 0.0

    # Acceleration = first-order diff of velocity
    if len(velocities) > 1:
        accel = np.diff(velocities)
        var_a = float(np.var(accel))
    else:
        var_a = 0.0

    b_mean = baseline_mean if baseline_mean is not None else tau
    b_std = baseline_std if baseline_std is not None else 1.0

    tau_dev = (tau - b_mean) / b_std if b_std > 1e-6 else 0.0
    stutters = detect_stutters(points, b_mean, b_std)

    t_start_ms = points[0].t
    t_end_ms = points[-1].t
    time_on_task = (t_end_ms - t_start_ms) / 1000.0

    window_start = datetime.fromtimestamp(t_start_ms / 1000.0, tz=timezone.utc)
    window_end = datetime.fromtimestamp(t_end_ms / 1000.0, tz=timezone.utc)

    return KinematicWindow(
        session_id=session_id,
        window_start=window_start,
        window_end=window_end,
        point_count=len(points),
        tortuosity=tau,
        mean_velocity=mean_v,
        velocity_variance=var_v,
        acceleration_variance=var_a,
        stutter_count=stutters,
        tau_deviation=tau_dev,
        time_on_task=time_on_task,
    )
