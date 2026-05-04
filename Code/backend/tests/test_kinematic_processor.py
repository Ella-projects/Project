from __future__ import annotations
import math

import pytest

from app.middleware.kinematic_processor import (
    compute_tortuosity,
    compute_velocities,
    detect_stutters,
    process_window,
)
from tests.conftest import high_tortuosity, right_angle, stationary, straight_line


# ── tortuosity ─────────────────────────────────────────────────────────────────

class TestTortuosity:
    def test_straight_line_is_one(self):
        pts = straight_line(n=20)
        assert compute_tortuosity(pts) == pytest.approx(1.0, rel=1e-6)

    def test_right_angle_is_sqrt2(self):
        pts = right_angle()
        tau = compute_tortuosity(pts)
        assert tau == pytest.approx(math.sqrt(2), rel=0.01)

    def test_stationary_returns_path_length_or_one(self):
        pts = stationary(n=10)
        tau = compute_tortuosity(pts)
        # displacement ≈ 0 → returns path_length (0) sentinel or 1.0
        assert tau >= 1.0 or tau == pytest.approx(0.0)

    def test_single_point_returns_one(self):
        from app.models.schemas.telemetry import MousePoint
        assert compute_tortuosity([MousePoint(x=0, y=0, t=0)]) == pytest.approx(1.0)

    def test_empty_returns_one(self):
        assert compute_tortuosity([]) == pytest.approx(1.0)

    def test_high_tortuosity_greater_than_straight(self):
        straight = compute_tortuosity(straight_line())
        zigzag   = compute_tortuosity(high_tortuosity())
        assert zigzag > straight

    def test_tau_always_gte_one_for_valid_paths(self):
        for pts in [straight_line(), right_angle()]:
            assert compute_tortuosity(pts) >= 1.0 - 1e-9


# ── velocities ─────────────────────────────────────────────────────────────────

class TestVelocities:
    def test_uniform_speed(self):
        """10px every 50ms → 0.2 px/ms per segment."""
        pts  = straight_line(n=10, dt=50.0)
        vels = compute_velocities(pts)
        assert len(vels) == 9
        assert all(abs(v - 0.2) < 1e-6 for v in vels)

    def test_zero_dt_segments_skipped(self):
        from app.models.schemas.telemetry import MousePoint
        pts = [
            MousePoint(x=0,  y=0, t=0),
            MousePoint(x=10, y=0, t=0),   # dt = 0 — skipped
            MousePoint(x=20, y=0, t=100),
        ]
        vels = compute_velocities(pts)
        assert len(vels) == 1

    def test_returns_numpy_array(self):
        import numpy as np
        vels = compute_velocities(straight_line())
        assert isinstance(vels, np.ndarray)


# ── stutters ───────────────────────────────────────────────────────────────────

class TestStutterDetection:
    def test_no_stutters_on_straight_line(self):
        pts = straight_line(n=30)
        count = detect_stutters(pts, baseline_mean=1.0, baseline_std=0.1)
        assert count == 0

    def test_stutters_detected_on_zigzag(self):
        pts = high_tortuosity()
        # baseline is straight-line τ = 1.0; zigzag will exceed threshold
        count = detect_stutters(pts, baseline_mean=1.0, baseline_std=0.1, alpha=2.0)
        assert count > 0

    def test_zero_std_returns_zero(self):
        pts = high_tortuosity()
        assert detect_stutters(pts, baseline_mean=1.0, baseline_std=0.0) == 0

    def test_too_few_points_returns_zero(self):
        pts = straight_line(n=4)
        assert detect_stutters(pts, baseline_mean=1.0, baseline_std=0.1) == 0


# ── process_window integration ─────────────────────────────────────────────────

class TestProcessWindow:
    def test_returns_kinematic_window(self):
        from app.models.schemas.telemetry import KinematicWindow
        pts = straight_line(n=20)
        kw  = process_window(pts, baseline_mean=1.0, baseline_std=0.1, session_id=99)
        assert isinstance(kw, KinematicWindow)

    def test_straight_line_tortuosity_is_one(self):
        pts = straight_line(n=20)
        kw  = process_window(pts, baseline_mean=1.0, baseline_std=0.1, session_id=99)
        assert kw.tortuosity == pytest.approx(1.0, rel=1e-5)

    def test_no_baseline_uses_default(self):
        pts = straight_line(n=20)
        kw  = process_window(pts, baseline_mean=None, baseline_std=None, session_id=99)
        assert kw.tau_deviation == pytest.approx(0.0, abs=1e-5)

    def test_time_on_task_matches_span(self):
        pts = straight_line(n=20, t_start=1000.0, dt=50.0)
        kw  = process_window(pts, baseline_mean=1.0, baseline_std=0.1, session_id=99)
        expected = (pts[-1].t - pts[0].t) / 1000.0
        assert kw.time_on_task == pytest.approx(expected, rel=1e-5)

    def test_point_count_correct(self):
        pts = straight_line(n=25)
        kw  = process_window(pts, baseline_mean=1.0, baseline_std=0.1, session_id=99)
        assert kw.point_count == 25
