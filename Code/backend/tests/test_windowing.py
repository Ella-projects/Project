from __future__ import annotations
import pytest

from app.middleware.windowing import WindowBuffer, WindowManager
from app.models.schemas.telemetry import MousePoint


def _pts(n: int, t_start: float = 0.0, dt: float = 50.0) -> list[MousePoint]:
    return [MousePoint(x=float(i), y=0.0, t=t_start + i * dt) for i in range(n)]


class TestWindowBuffer:
    def test_no_window_emitted_before_5s(self):
        buf = WindowBuffer(session_id=1)
        # 4.9 seconds worth of points (dt=50ms → 98 points = 4.9s)
        pts = _pts(98, dt=50.0)
        completed = buf.ingest(pts)
        assert completed == []

    def test_window_emitted_at_5s_boundary(self):
        buf = WindowBuffer(session_id=2)
        # 5 seconds + 1 extra point to trigger flush
        pts = _pts(102, dt=50.0)  # 101 intervals = 5.05s
        completed = buf.ingest(pts)
        assert len(completed) == 1

    def test_two_windows_emitted_for_10s(self):
        buf = WindowBuffer(session_id=3)
        pts = _pts(202, dt=50.0)  # ~10s
        completed = buf.ingest(pts)
        assert len(completed) == 2

    def test_sparse_window_not_emitted(self):
        """Windows with fewer than min_points_per_window are discarded."""
        from app.core.config import settings
        buf = WindowBuffer(session_id=4)
        # Only 5 points spread over 6 seconds — below min_points threshold
        pts = [MousePoint(x=float(i), y=0.0, t=i * 1200.0) for i in range(5)]
        completed = buf.ingest(pts)
        assert completed == []

    def test_flush_returns_remaining_points(self):
        buf = WindowBuffer(session_id=5)
        pts = _pts(30, dt=50.0)  # 1.5s — not enough for a full window
        buf.ingest(pts)
        flushed = buf.flush()
        assert flushed is not None
        assert len(flushed) == 30

    def test_flush_returns_none_when_below_min_points(self):
        buf = WindowBuffer(session_id=6)
        pts = _pts(3, dt=50.0)
        buf.ingest(pts)
        assert buf.flush() is None

    def test_incremental_ingestion(self):
        """Points arriving in small batches should behave identically to one large batch."""
        buf1 = WindowBuffer(session_id=7)
        buf2 = WindowBuffer(session_id=8)
        all_pts = _pts(202, dt=50.0)

        c1 = buf1.ingest(all_pts)

        c2 = []
        for i in range(0, len(all_pts), 10):
            c2.extend(buf2.ingest(all_pts[i:i+10]))

        assert len(c1) == len(c2)

    def test_window_points_are_correct_slice(self):
        buf = WindowBuffer(session_id=9)
        pts = _pts(102, dt=50.0)
        completed = buf.ingest(pts)
        assert len(completed) == 1
        # Window should contain points from t=0 up to the 5s boundary
        first_t = completed[0][0].t
        last_t  = completed[0][-1].t
        assert last_t - first_t >= 5000.0 * 0.95  # within 5% tolerance


class TestWindowManager:
    def test_get_creates_buffer(self):
        mgr = WindowManager()
        buf = mgr.get(session_id=100)
        assert isinstance(buf, WindowBuffer)

    def test_get_returns_same_buffer(self):
        mgr = WindowManager()
        assert mgr.get(1) is mgr.get(1)

    def test_remove_clears_buffer(self):
        mgr = WindowManager()
        mgr.get(session_id=200)
        mgr.remove(session_id=200)
        # After removal, a new buffer is created
        new_buf = mgr.get(session_id=200)
        assert new_buf.flush() is None
