from __future__ import annotations
"""
Segmented Windowing Layer

Buffers incoming MousePoints and emits discrete 5-second temporal windows
to the kinematic processor. Operates per-session.
"""

from collections import defaultdict
from datetime import datetime, timezone

from app.core.config import settings
from app.models.schemas.telemetry import MousePoint


class WindowBuffer:
    """
    Per-session ring buffer.  Points older than window_duration are flushed
    into a completed window and forwarded to the kinematic processor.
    """

    def __init__(self, session_id: int) -> None:
        self.session_id = session_id
        self._points: list[MousePoint] = []
        self._window_open_ts: float | None = None

    def ingest(self, points: list[MousePoint]) -> list[list[MousePoint]]:
        """
        Add points to the buffer.  Returns a list of completed windows
        (each window is a list of MousePoints) ready for kinematic processing.
        """
        completed: list[list[MousePoint]] = []

        for point in points:
            if self._window_open_ts is None:
                self._window_open_ts = point.t

            self._points.append(point)

            elapsed_ms = point.t - self._window_open_ts
            if elapsed_ms >= settings.window_duration_seconds * 1000:
                if len(self._points) >= settings.min_points_per_window:
                    completed.append(list(self._points))
                self._points = []
                self._window_open_ts = point.t

        return completed

    def flush(self) -> list[MousePoint] | None:
        """Force-flush any remaining points (e.g. on session end)."""
        if len(self._points) >= settings.min_points_per_window:
            result = list(self._points)
            self._points = []
            self._window_open_ts = None
            return result
        return None


class WindowManager:
    """Registry of per-session WindowBuffers."""

    def __init__(self) -> None:
        self._buffers: dict[int, WindowBuffer] = defaultdict(WindowBuffer)

    def get(self, session_id: int) -> WindowBuffer:
        if session_id not in self._buffers:
            self._buffers[session_id] = WindowBuffer(session_id)
        return self._buffers[session_id]

    def remove(self, session_id: int) -> None:
        self._buffers.pop(session_id, None)


# Singleton used by the WebSocket route
window_manager = WindowManager()
