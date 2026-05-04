from __future__ import annotations
import pytest

from app.engine.risk_model import compute_risk, interpret_risk


class TestComputeRisk:
    def test_zero_fatigue_gives_zero(self):
        # No fatigue → no risk regardless of bias
        assert compute_risk(0.0, 1.5, 0.0, 0.0) == pytest.approx(0.0)

    def test_zero_bias_all_dimensions_gives_zero(self):
        # No bias in any dimension → no risk
        assert compute_risk(0.8, 0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_both_zero_gives_zero(self):
        assert compute_risk(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_max_inputs_give_one(self):
        # w_fatigue=1, dominant bias=±2 → P = 1 × (2/2) = 1.0
        assert compute_risk(1.0, 2.0,  0.0, 0.0) == pytest.approx(1.0)
        assert compute_risk(1.0, -2.0, 0.0, 0.0) == pytest.approx(1.0)
        assert compute_risk(1.0, 0.0,  2.0, 0.0) == pytest.approx(1.0)
        assert compute_risk(1.0, 0.0,  0.0, 2.0) == pytest.approx(1.0)

    def test_midpoint(self):
        # w_fatigue=0.5, dominant bias=1.0 → P = 0.5 × (1/2) = 0.25
        assert compute_risk(0.5, 1.0, 0.0, 0.0) == pytest.approx(0.25)

    def test_bias_is_absolute(self):
        # Positive and negative bias of same magnitude give same P
        assert compute_risk(0.6, 1.4, 0.0, 0.0) == compute_risk(0.6, -1.4, 0.0, 0.0)

    def test_bias_clamped_at_two(self):
        # D-scores > 2 are out of range but should not cause P > 1
        assert compute_risk(1.0, 5.0, 0.0, 0.0) == pytest.approx(1.0)

    def test_max_dimension_drives_risk(self):
        # Race bias is highest — should determine P regardless of age/gender values
        assert compute_risk(1.0, 0.2, 0.3, 1.8) == pytest.approx(
            compute_risk(1.0, 1.8, 0.0, 0.0)
        )

    def test_all_dimensions_same_gives_same_as_one(self):
        # max(x, x, x) == x so same as passing one dominant value
        assert compute_risk(0.7, 1.0, 1.0, 1.0) == pytest.approx(
            compute_risk(0.7, 1.0, 0.0, 0.0)
        )

    def test_result_in_unit_interval(self):
        for w in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for s in [-2.0, -1.0, 0.0, 1.0, 2.0]:
                p = compute_risk(w, s, s * 0.5, s * 0.8)
                assert 0.0 <= p <= 1.0


class TestInterpretRisk:
    @pytest.mark.parametrize("p, expected", [
        (0.05, "negligible"),
        (0.20, "low"),
        (0.40, "moderate"),
        (0.70, "high"),
        (1.00, "high"),
    ])
    def test_thresholds(self, p, expected):
        assert interpret_risk(p) == expected
