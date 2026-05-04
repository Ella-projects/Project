from __future__ import annotations
"""
Risk Multiplier Model

P = W_fatigue × S_bias

Combines the real-time fatigue coefficient from the StateMonitor with the
user's latent IAT D-score to produce a composite risk probability P ∈ [0, 1].

The product model reflects the theoretical claim that fatigue amplifies
the expression of implicit bias: a highly biased but alert user may still
perform accurately, but a fatigued biased user is at elevated error risk.
"""


def compute_risk(
    w_fatigue: float,
    s_bias_age: float,
    s_bias_gender: float,
    s_bias_race: float,
) -> float:
    """
    P = W_fatigue × max(|S_bias_age|, |S_bias_gender|, |S_bias_race|) / 2

    Uses the most extreme bias score across all three IAT dimensions so that
    strong implicit bias in any single dimension drives the risk score.
    D-score range ≈ [-2, 2]; dividing by 2 normalises to [0, 1].

    Returns P ∈ [0, 1].
    """
    composite = max(abs(s_bias_age), abs(s_bias_gender), abs(s_bias_race))
    normalized = min(composite / 2.0, 1.0)
    p = w_fatigue * normalized
    return round(float(p), 4)


def interpret_risk(p: float) -> str:
    """
    Maps P to a human-readable risk tier for UI display.

    Thresholds are placeholder — calibrate against outcome data.
    """
    if p >= 0.60:
        return "high"
    elif p >= 0.35:
        return "moderate"
    elif p >= 0.15:
        return "low"
    else:
        return "negligible"
