from __future__ import annotations
"""
Decision Rule Generator

Produces symbolic IF-THEN rules from the session's InformationSystem.

Two rule sources, used in priority order:
  1. Induced rules  — derived from IS equivalence classes (RST-based).
     Available once IS.size ≥ MIN_OBJECTS_FOR_RST.
  2. Template rules — static domain-knowledge rules used as fallback
     when there is insufficient session history.

Rules are returned as plain text strings for display in the HardNudge modal.
"""

from app.engine.information_system import InducedRule, is_registry


# ─────────────────────────────────────────────────────────────────────────────
# Static template rules (domain knowledge fallback)
# ─────────────────────────────────────────────────────────────────────────────

_TEMPLATES: dict[str, list[str]] = {
    "high_tau_fatigue": [
        "IF tortuosity > 2σ above baseline AND fatigue_coefficient > 0.6 "
        "THEN high_risk [certainty: 0.82]"
    ],
    "high_stutter_bias": [
        "IF stutter_count ≥ 2 in window AND latent_bias_score > 0.5 "
        "THEN high_risk [certainty: 0.74]"
    ],
    "boundary_tau": [
        "IF tortuosity 1–2σ above baseline "
        "THEN boundary_risk [certainty: 0.55]"
    ],
    "boundary_fatigue": [
        "IF fatigue_coefficient 0.35–0.60 AND velocity_variance elevated "
        "THEN boundary_risk [certainty: 0.50]"
    ],
}


def _select_templates(
    tau_deviation: float,
    stutter_count: int,
    w_fatigue: float,
    s_bias: float,
    classification: str,
) -> list[str]:
    fired: list[str] = []
    if classification == "positive_region":
        if tau_deviation > 2.0 and w_fatigue > 0.6:
            fired.extend(_TEMPLATES["high_tau_fatigue"])
        if stutter_count >= 2 and abs(s_bias) > 0.5:
            fired.extend(_TEMPLATES["high_stutter_bias"])
        if not fired:
            fired.append(
                "IF composite risk score ≥ lower approximation threshold "
                "THEN high_risk [certainty: 0.75]"
            )
    elif classification == "boundary_region":
        if tau_deviation > 1.0:
            fired.extend(_TEMPLATES["boundary_tau"])
        if w_fatigue > 0.35:
            fired.extend(_TEMPLATES["boundary_fatigue"])
        if not fired:
            fired.append(
                "IF composite risk score in boundary region "
                "THEN boundary_risk [certainty: 0.50]"
            )
    return fired


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def generate_rules(
    session_id: int,
    window_id: int,
    tau_deviation: float,
    stutter_count: int,
    w_fatigue: float,
    s_bias: float,
    classification: str,
    max_rules: int = 4,
) -> list[str]:
    """
    Returns a list of rule strings (≤ max_rules) for display in the nudge modal.

    Attempts IS-induced rules first; falls back to static templates.
    """
    is_sys = is_registry.get_or_create(session_id)
    induced: list[InducedRule] = is_sys.get_rules(certainty_threshold=0.5)

    # Filter to rules that match the current classification
    target_consequent = "high_risk" if classification == "positive_region" else "boundary_risk"
    matching = [r for r in induced if r.consequent == target_consequent]

    if matching:
        return [r.to_text() for r in matching[:max_rules]]

    # Fallback to static templates
    return _select_templates(tau_deviation, stutter_count, w_fatigue, s_bias, classification)[:max_rules]
