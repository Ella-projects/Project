from __future__ import annotations
import pytest

from app.engine.information_system import (
    HIGH_RISK,
    LOW_RISK,
    InformationSystem,
    LabeledObject,
    bootstrap_label,
    discretize,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_attrs(
    tortuosity: float = 1.0,
    tau_deviation: float = 0.0,
    stutter_count: float = 0.0,
    velocity_variance: float = 10.0,
    acceleration_variance: float = 5.0,
    time_on_task: float = 3.0,
    w_fatigue: float = 0.1,
    s_bias: float = 0.0,
) -> dict:
    return {
        "tortuosity": tortuosity,
        "tau_deviation": tau_deviation,
        "stutter_count": stutter_count,
        "velocity_variance": velocity_variance,
        "acceleration_variance": acceleration_variance,
        "time_on_task": time_on_task,
        "w_fatigue": w_fatigue,
        "s_bias": s_bias,
    }


def _make_obj(window_id: int, attrs: dict, label: int, case_id: int | None = None) -> LabeledObject:
    return LabeledObject(
        window_id=window_id,
        case_id=case_id,
        attrs=attrs,
        discretized=discretize(attrs),
        label=label,
        label_source="test",
    )


def _populated_is(n_high: int = 10, n_low: int = 10) -> InformationSystem:
    """
    Returns an IS with n_high high-risk and n_low low-risk objects,
    all sharing the same attribute vector within each group.
    """
    is_sys = InformationSystem(session_id=1)

    high_attrs = _make_attrs(tau_deviation=2.5, stutter_count=3.0, w_fatigue=0.8)
    low_attrs  = _make_attrs(tau_deviation=0.2, stutter_count=0.0, w_fatigue=0.1)

    for i in range(n_high):
        is_sys.add_object(_make_obj(i, high_attrs, HIGH_RISK, case_id=1))

    for i in range(n_low):
        is_sys.add_object(_make_obj(n_high + i, low_attrs, LOW_RISK, case_id=2))

    return is_sys


# ── discretise ─────────────────────────────────────────────────────────────────

class TestDiscretize:
    def test_returns_tuple_of_correct_length(self):
        vec = discretize(_make_attrs())
        assert isinstance(vec, tuple)
        assert len(vec) == 8  # one per attribute

    def test_baseline_tortuosity_bin_zero(self):
        # τ = 1.05 < 1.2 → bin 0
        vec = discretize(_make_attrs(tortuosity=1.05))
        assert vec[0] == 0

    def test_elevated_tortuosity_bin_two(self):
        # τ = 1.7, cut-points [1.2, 1.5, 2.0] → bin 2
        vec = discretize(_make_attrs(tortuosity=1.7))
        assert vec[0] == 2

    def test_severe_tortuosity_bin_three(self):
        vec = discretize(_make_attrs(tortuosity=2.5))
        assert vec[0] == 3

    def test_negative_tau_deviation_bin_zero(self):
        # tau_dev = -0.5 < 0.0 → bin 0
        vec = discretize(_make_attrs(tau_deviation=-0.5))
        assert vec[1] == 0

    def test_stutter_zero_bin_zero(self):
        vec = discretize(_make_attrs(stutter_count=0))
        assert vec[2] == 0

    def test_stutter_three_plus_bin_three(self):
        vec = discretize(_make_attrs(stutter_count=3))
        assert vec[2] == 3

    def test_same_attrs_same_vector(self):
        a1 = _make_attrs(tortuosity=1.6, tau_deviation=1.2)
        a2 = _make_attrs(tortuosity=1.6, tau_deviation=1.2)
        assert discretize(a1) == discretize(a2)

    def test_different_attrs_different_vector(self):
        a1 = _make_attrs(tortuosity=1.1)
        a2 = _make_attrs(tortuosity=2.5)
        assert discretize(a1) != discretize(a2)


# ── bootstrap label ────────────────────────────────────────────────────────────

class TestBootstrapLabel:
    def test_high_tau_and_stutters_is_high_risk(self):
        attrs = _make_attrs(tau_deviation=2.5, stutter_count=2.0)
        assert bootstrap_label(attrs) == HIGH_RISK

    def test_high_fatigue_and_tau_is_high_risk(self):
        attrs = _make_attrs(tau_deviation=1.6, w_fatigue=0.7)
        assert bootstrap_label(attrs) == HIGH_RISK

    def test_extreme_tau_alone_is_high_risk(self):
        attrs = _make_attrs(tau_deviation=3.5)
        assert bootstrap_label(attrs) == HIGH_RISK

    def test_normal_attrs_is_low_risk(self):
        attrs = _make_attrs(tau_deviation=0.5, stutter_count=0.0, w_fatigue=0.2)
        assert bootstrap_label(attrs) == LOW_RISK

    def test_boundary_tau_without_stutters_is_low_risk(self):
        # tau_dev = 2.1 alone (no stutters, low fatigue) → LOW_RISK
        attrs = _make_attrs(tau_deviation=2.1, stutter_count=0.0, w_fatigue=0.1)
        assert bootstrap_label(attrs) == LOW_RISK


# ── IS classification ──────────────────────────────────────────────────────────

class TestInformationSystemClassify:
    def test_insufficient_data_returns_sentinel(self):
        is_sys = InformationSystem(session_id=2)
        vec = discretize(_make_attrs())
        region, certainty = is_sys.classify(vec)
        assert region == "insufficient_data"
        assert certainty == 0.0

    def test_positive_region_all_high_risk_class(self):
        is_sys = _populated_is(n_high=10, n_low=10)
        high_attrs = _make_attrs(tau_deviation=2.5, stutter_count=3.0, w_fatigue=0.8)
        region, certainty = is_sys.classify(discretize(high_attrs))
        assert region == "positive_region"
        assert certainty == pytest.approx(1.0)

    def test_negative_region_all_low_risk_class(self):
        is_sys = _populated_is(n_high=10, n_low=10)
        low_attrs = _make_attrs(tau_deviation=0.2, stutter_count=0.0, w_fatigue=0.1)
        region, certainty = is_sys.classify(discretize(low_attrs))
        assert region == "negative_region"
        assert certainty == pytest.approx(0.0)

    def test_boundary_region_mixed_class(self):
        is_sys = InformationSystem(session_id=3)
        # Same attr vector, mixed labels → boundary
        attrs = _make_attrs(tau_deviation=1.5, stutter_count=1.0, w_fatigue=0.4)
        for i in range(8):
            is_sys.add_object(_make_obj(i,    attrs, HIGH_RISK))
        for i in range(8, 20):
            is_sys.add_object(_make_obj(i, attrs, LOW_RISK))

        region, certainty = is_sys.classify(discretize(attrs))
        assert region == "boundary_region"
        assert 0.0 < certainty < 1.0

    def test_certainty_reflects_class_composition(self):
        is_sys = InformationSystem(session_id=4)
        attrs = _make_attrs(tau_deviation=1.5, stutter_count=1.0)
        # 6 high_risk + 4 low_risk in same class → certainty = 6/10 = 0.6
        for i in range(6):
            is_sys.add_object(_make_obj(i, attrs, HIGH_RISK))
        for i in range(6, 10):
            is_sys.add_object(_make_obj(i, attrs, LOW_RISK))
        # Pad with unrelated objects to reach MIN_OBJECTS_FOR_RST (15)
        other_attrs = _make_attrs(tau_deviation=0.1, stutter_count=0.0)
        for i in range(10, 15):
            is_sys.add_object(_make_obj(i, other_attrs, LOW_RISK))

        _, certainty = is_sys.classify(discretize(attrs))
        assert certainty == pytest.approx(6 / 10, rel=0.01)


# ── label updates ──────────────────────────────────────────────────────────────

class TestLabelUpdates:
    def test_update_labels_for_case_correct_decision(self):
        """Correct decision → windows relabelled LOW_RISK."""
        is_sys = InformationSystem(session_id=5)
        attrs  = _make_attrs(tau_deviation=2.5, stutter_count=2.0)
        for i in range(5):
            is_sys.add_object(_make_obj(i, attrs, HIGH_RISK, case_id=10))

        is_sys.update_labels_for_case(case_id=10, is_correct=True)
        labels = [o.label for o in is_sys._objects]
        assert all(l == LOW_RISK for l in labels)

    def test_update_labels_for_case_incorrect_decision(self):
        """Incorrect decision → windows relabelled HIGH_RISK."""
        is_sys = InformationSystem(session_id=6)
        attrs  = _make_attrs()
        for i in range(5):
            is_sys.add_object(_make_obj(i, attrs, LOW_RISK, case_id=11))

        is_sys.update_labels_for_case(case_id=11, is_correct=False)
        labels = [o.label for o in is_sys._objects]
        assert all(l == HIGH_RISK for l in labels)

    def test_update_only_affects_specified_case(self):
        is_sys = InformationSystem(session_id=7)
        attrs  = _make_attrs()
        is_sys.add_object(_make_obj(0, attrs, LOW_RISK, case_id=20))
        is_sys.add_object(_make_obj(1, attrs, LOW_RISK, case_id=21))

        is_sys.update_labels_for_case(case_id=20, is_correct=False)

        assert is_sys._objects[0].label == HIGH_RISK  # case 20 updated
        assert is_sys._objects[1].label == LOW_RISK   # case 21 untouched

    def test_update_label_by_window(self):
        is_sys = InformationSystem(session_id=8)
        attrs  = _make_attrs()
        is_sys.add_object(_make_obj(42, attrs, LOW_RISK))
        is_sys.update_label_by_window(window_id=42, label=HIGH_RISK, source="adherence")
        assert is_sys._objects[0].label == HIGH_RISK
        assert is_sys._objects[0].label_source == "adherence"


# ── rule induction ─────────────────────────────────────────────────────────────

class TestRuleInduction:
    def test_no_rules_when_insufficient_data(self):
        is_sys = InformationSystem(session_id=9)
        assert is_sys.induce_rules() == []

    def test_rules_generated_from_positive_region(self):
        is_sys = _populated_is(n_high=10, n_low=10)
        rules  = is_sys.induce_rules(certainty_threshold=0.5)
        assert len(rules) > 0

    def test_all_rules_have_required_fields(self):
        is_sys = _populated_is(n_high=10, n_low=10)
        for rule in is_sys.induce_rules():
            assert isinstance(rule.conditions, list)
            assert len(rule.conditions) > 0
            assert 0.0 < rule.certainty <= 1.0
            assert rule.support > 0
            assert rule.consequent in ("high_risk", "boundary_risk")

    def test_positive_region_rules_have_certainty_one(self):
        """Equivalence classes entirely within X give certainty = 1.0."""
        is_sys = _populated_is(n_high=10, n_low=10)
        rules  = is_sys.induce_rules(certainty_threshold=0.99)
        for rule in rules:
            assert rule.certainty == pytest.approx(1.0)

    def test_rules_sorted_by_certainty_desc(self):
        is_sys = _populated_is(n_high=10, n_low=10)
        # Add a boundary class (mixed labels)
        mixed_attrs = _make_attrs(tau_deviation=1.2, stutter_count=1.0)
        for i in range(20, 30):
            label = HIGH_RISK if i % 2 == 0 else LOW_RISK
            is_sys.add_object(_make_obj(i, mixed_attrs, label))

        rules = is_sys.induce_rules(certainty_threshold=0.0)
        certainties = [r.certainty for r in rules]
        assert certainties == sorted(certainties, reverse=True)

    def test_rule_to_text_format(self):
        is_sys = _populated_is(n_high=10, n_low=10)
        rules  = is_sys.induce_rules()
        for rule in rules:
            text = rule.to_text()
            assert text.startswith("IF ")
            assert "THEN" in text
            assert "certainty" in text
