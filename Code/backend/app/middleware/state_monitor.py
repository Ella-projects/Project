from __future__ import annotations
"""
State-Aware Logic Layer

Monitors session-level trends in kinematic windows to:
  1. Update the rolling fatigue coefficient W_fatigue
  2. Flag sustained tremor / movement instability
  3. Emit alerts when performance decline is detected
"""

from collections import deque

import numpy as np


class SessionStateMonitor:
    """
    Maintains a rolling history of kinematic windows for a single session
    and derives the fatigue coefficient W_fatigue ∈ [0, 1].

    W_fatigue is computed from:
      - Trend in tortuosity τ (increasing τ over time → fatigue)
      - Trend in velocity variance (increasing variability → fatigue)
      - Stutter frequency (stutters-per-window rolling average)

    TODO: Weight factors below are placeholder — calibrate from empirical data.
    """

    _HISTORY_WINDOW = 12  # number of kinematic windows to consider (~60s)
    _TAU_WEIGHT = 0.4
    _VAR_WEIGHT = 0.3
    _STUTTER_WEIGHT = 0.3

    def __init__(self, session_id: int, baseline_tau: float = 1.0) -> None:
        self.session_id = session_id
        self.baseline_tau = baseline_tau
        self._tau_history: deque[float] = deque(maxlen=self._HISTORY_WINDOW)
        self._var_history: deque[float] = deque(maxlen=self._HISTORY_WINDOW)
        self._stutter_history: deque[int] = deque(maxlen=self._HISTORY_WINDOW)
        self.w_fatigue: float = 0.0
        self.instability_flag: bool = False

    def update(
        self,
        tortuosity: float,
        velocity_variance: float,
        stutter_count: int,
    ) -> float:
        """
        Ingest one kinematic window result and return updated W_fatigue.
        """
        self._tau_history.append(tortuosity)
        self._var_history.append(velocity_variance)
        self._stutter_history.append(stutter_count)

        self.w_fatigue = self._compute_fatigue()
        self.instability_flag = self._detect_instability()

        return self.w_fatigue

    def _compute_fatigue(self) -> float:
        """
        Combines three normalized sub-scores into W_fatigue.

        TODO: Replace linear combination with a learned model once
              sufficient session data is available.
        """
        tau_score = self._tau_trend_score()
        var_score = self._variance_trend_score()
        stutter_score = self._stutter_score()

        raw = (
            self._TAU_WEIGHT * tau_score
            + self._VAR_WEIGHT * var_score
            + self._STUTTER_WEIGHT * stutter_score
        )
        return float(np.clip(raw, 0.0, 1.0))

    def _tau_trend_score(self) -> float:
        """
        Measures upward trend in τ relative to baseline.
        Score = 0 if τ is at baseline; 1 if τ has doubled.

        TODO: Use linear regression slope for robustness.
        """
        if len(self._tau_history) < 2:
            return 0.0
        recent_mean = np.mean(list(self._tau_history)[-4:])
        ratio = (recent_mean - self.baseline_tau) / max(self.baseline_tau, 1e-6)
        return float(np.clip(ratio, 0.0, 1.0))

    def _variance_trend_score(self) -> float:
        """Score based on recent velocity variance relative to session-start variance."""
        if len(self._var_history) < 4:
            return 0.0
        early = np.mean(list(self._var_history)[:4])
        recent = np.mean(list(self._var_history)[-4:])
        if early < 1e-6:
            return 0.0
        ratio = (recent - early) / early
        return float(np.clip(ratio, 0.0, 1.0))

    def _stutter_score(self) -> float:
        """Fraction of recent windows that contained at least one stutter."""
        if not self._stutter_history:
            return 0.0
        return float(np.mean([1 if s > 0 else 0 for s in self._stutter_history]))

    def _detect_instability(self) -> bool:
        """
        Flag sustained instability: τ > 2× baseline for 3+ consecutive windows.

        TODO: Incorporate accelerometer / tremor frequency analysis if
              hardware input is available.
        """
        if len(self._tau_history) < 3:
            return False
        last_three = list(self._tau_history)[-3:]
        return all(t > 2.0 * self.baseline_tau for t in last_three)


class StateMonitorRegistry:
    """Maps session_id → SessionStateMonitor."""

    def __init__(self) -> None:
        self._monitors: dict[int, SessionStateMonitor] = {}

    def get_or_create(self, session_id: int, baseline_tau: float = 1.0) -> SessionStateMonitor:
        if session_id not in self._monitors:
            self._monitors[session_id] = SessionStateMonitor(session_id, baseline_tau)
        return self._monitors[session_id]

    def remove(self, session_id: int) -> None:
        self._monitors.pop(session_id, None)


state_registry = StateMonitorRegistry()
