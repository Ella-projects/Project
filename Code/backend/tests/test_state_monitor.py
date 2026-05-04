from __future__ import annotations
import pytest

from app.middleware.state_monitor import SessionStateMonitor, StateMonitorRegistry


class TestSessionStateMonitor:
    def test_initial_fatigue_is_zero(self):
        monitor = SessionStateMonitor(session_id=1, baseline_tau=1.0)
        assert monitor.w_fatigue == 0.0

    def test_fatigue_increases_with_high_tortuosity(self):
        monitor = SessionStateMonitor(session_id=2, baseline_tau=1.0)
        for _ in range(12):
            monitor.update(tortuosity=2.5, velocity_variance=300.0, stutter_count=2)
        assert monitor.w_fatigue > 0.0

    def test_fatigue_stays_low_at_baseline(self):
        monitor = SessionStateMonitor(session_id=3, baseline_tau=1.0)
        for _ in range(12):
            monitor.update(tortuosity=1.05, velocity_variance=20.0, stutter_count=0)
        assert monitor.w_fatigue < 0.3

    def test_fatigue_clamped_to_unit_interval(self):
        monitor = SessionStateMonitor(session_id=4, baseline_tau=1.0)
        for _ in range(20):
            monitor.update(tortuosity=10.0, velocity_variance=1000.0, stutter_count=3)
        assert 0.0 <= monitor.w_fatigue <= 1.0

    def test_fatigue_increases_monotonically_under_stress(self):
        monitor = SessionStateMonitor(session_id=5, baseline_tau=1.0)
        prev = 0.0
        for _ in range(12):
            w = monitor.update(tortuosity=3.0, velocity_variance=500.0, stutter_count=3)
            assert w >= prev - 1e-9  # allow tiny float noise
            prev = w

    def test_instability_flag_off_initially(self):
        monitor = SessionStateMonitor(session_id=6, baseline_tau=1.0)
        assert monitor.instability_flag is False

    def test_instability_flag_set_after_three_high_tau_windows(self):
        monitor = SessionStateMonitor(session_id=7, baseline_tau=1.0)
        for _ in range(3):
            monitor.update(tortuosity=2.5, velocity_variance=100.0, stutter_count=0)
        # 2.5 > 2 × 1.0 → instability
        assert monitor.instability_flag is True

    def test_instability_flag_not_set_with_only_two_high_windows(self):
        monitor = SessionStateMonitor(session_id=8, baseline_tau=1.0)
        monitor.update(tortuosity=2.5, velocity_variance=100.0, stutter_count=0)
        monitor.update(tortuosity=2.5, velocity_variance=100.0, stutter_count=0)
        monitor.update(tortuosity=1.0, velocity_variance=20.0,  stutter_count=0)
        assert monitor.instability_flag is False

    def test_stutter_contributes_to_fatigue(self):
        no_stutter = SessionStateMonitor(session_id=9,  baseline_tau=1.0)
        with_stutter = SessionStateMonitor(session_id=10, baseline_tau=1.0)

        for _ in range(12):
            no_stutter.update(tortuosity=1.1, velocity_variance=30.0, stutter_count=0)
            with_stutter.update(tortuosity=1.1, velocity_variance=30.0, stutter_count=3)

        assert with_stutter.w_fatigue > no_stutter.w_fatigue

    def test_history_limited_to_12_windows(self):
        """Old windows should not permanently inflate fatigue."""
        monitor = SessionStateMonitor(session_id=11, baseline_tau=1.0)
        # Pump in 12 high-stress windows
        for _ in range(12):
            monitor.update(tortuosity=3.0, velocity_variance=800.0, stutter_count=3)
        high_fatigue = monitor.w_fatigue

        # Then 12 resting windows — fatigue should decrease
        for _ in range(12):
            monitor.update(tortuosity=1.0, velocity_variance=10.0, stutter_count=0)
        assert monitor.w_fatigue < high_fatigue


class TestStateMonitorRegistry:
    def test_get_or_create_returns_monitor(self):
        reg = StateMonitorRegistry()
        m = reg.get_or_create(session_id=1)
        assert isinstance(m, SessionStateMonitor)

    def test_same_session_same_monitor(self):
        reg = StateMonitorRegistry()
        assert reg.get_or_create(1) is reg.get_or_create(1)

    def test_remove_clears_session(self):
        reg = StateMonitorRegistry()
        m1 = reg.get_or_create(99)
        reg.remove(99)
        m2 = reg.get_or_create(99)
        assert m1 is not m2
