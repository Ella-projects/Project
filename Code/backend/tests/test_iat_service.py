from __future__ import annotations
import pytest

from app.services.iat_service import (
    build_block_specs,
    compute_d_score,
    generate_stimuli_for_block,
    interpret_d_score,
)
from tests.conftest import make_trial


# ── block structure ────────────────────────────────────────────────────────────

class TestBlockSpecs:
    def test_seven_blocks_generated(self):
        specs = build_block_specs(20, 20, 40)
        assert len(specs) == 7

    def test_block_numbers_sequential(self):
        specs = build_block_specs(20, 20, 40)
        assert [s.block_number for s in specs] == [1, 2, 3, 4, 5, 6, 7]

    def test_practice_blocks_correct(self):
        specs = build_block_specs(20, 20, 40)
        practice = [s.block_number for s in specs if s.is_practice]
        assert practice == [1, 2, 5]

    def test_test_blocks_correct(self):
        specs = build_block_specs(20, 20, 40)
        test_blocks = [s.block_number for s in specs if not s.is_practice]
        assert test_blocks == [3, 4, 6, 7]

    def test_compatible_mapping_blocks_3_4(self):
        specs = build_block_specs(20, 20, 40)
        b3 = specs[2]
        assert "Elderly" in b3.left_categories
        assert "High Acuity" in b3.left_categories

    def test_incompatible_mapping_blocks_6_7(self):
        specs = build_block_specs(20, 20, 40)
        b6 = specs[5]
        assert "Young" in b6.left_categories
        assert "High Acuity" in b6.left_categories


class TestGenerateStimuli:
    def test_returns_correct_trial_count(self):
        specs = build_block_specs(20, 20, 40)
        stimuli = generate_stimuli_for_block(specs[2])  # block 3 — 20 trials
        assert len(stimuli) == pytest.approx(20, abs=2)  # ±2 for rounding

    def test_trial_numbers_sequential(self):
        specs = build_block_specs(20, 20, 40)
        stimuli = generate_stimuli_for_block(specs[0])
        assert [s.trial_number for s in stimuli] == list(range(1, len(stimuli) + 1))

    def test_all_stimuli_have_correct_key(self):
        specs = build_block_specs(20, 20, 40)
        for spec in specs:
            for s in generate_stimuli_for_block(spec):
                assert s.correct_key in ("e", "i")

    def test_correct_key_matches_category_mapping(self):
        specs = build_block_specs(20, 20, 40)
        b3 = specs[2]  # Elderly + High Acuity = e; Young + Low Acuity = i
        for s in generate_stimuli_for_block(b3):
            if s.category in b3.left_categories:
                assert s.correct_key == "e"
            else:
                assert s.correct_key == "i"


# ── D-score computation ────────────────────────────────────────────────────────

class TestDScore:
    def _symmetric_trials(self, rt: int = 700) -> list[dict]:
        """Both compatible and incompatible blocks have identical RT → D = 0."""
        trials = []
        for block in [3, 4, 6, 7]:
            for _ in range(20):
                trials.append(make_trial(block, rt))
        return trials

    def test_equal_rts_gives_zero_d(self):
        result = compute_d_score(self._symmetric_trials())
        assert result["d_score"] == pytest.approx(0.0, abs=0.01)

    def test_slower_incompatible_gives_positive_d(self):
        """Incompatible (blocks 6, 7) slower → positive D (pro-stereotypical bias)."""
        trials = []
        for block in [3, 4]:
            trials += [make_trial(block, 600) for _ in range(20)]
        for block in [6, 7]:
            trials += [make_trial(block, 900) for _ in range(20)]
        result = compute_d_score(trials)
        assert result["d_score"] > 0

    def test_slower_compatible_gives_negative_d(self):
        trials = []
        for block in [3, 4]:
            trials += [make_trial(block, 900) for _ in range(20)]
        for block in [6, 7]:
            trials += [make_trial(block, 600) for _ in range(20)]
        result = compute_d_score(trials)
        assert result["d_score"] < 0

    def test_fast_trials_excluded(self):
        """Trials with RT < 300ms must be excluded from D-score calculation."""
        trials = self._symmetric_trials(rt=700)
        # Add fast trials to compatible blocks — should not shift D
        for block in [3, 4]:
            trials += [make_trial(block, 100) for _ in range(5)]
        result = compute_d_score(trials)
        assert abs(result["d_score"]) < 0.1

    def test_error_penalty_applied(self):
        """Error trials get block_mean + 600ms — errors in incompatible blocks raise D."""
        trials = [make_trial(b, 700) for b in [3, 4, 6, 7] for _ in range(19)]
        trials.append(make_trial(6, 700, correct=False))  # one error in block 6
        result_with_error = compute_d_score(trials)

        clean_trials = [make_trial(b, 700) for b in [3, 4, 6, 7] for _ in range(20)]
        result_clean = compute_d_score(clean_trials)

        assert result_with_error["d_score"] > result_clean["d_score"]

    def test_practice_trials_excluded(self):
        trials = self._symmetric_trials()
        trials += [make_trial(1, 500, practice=True) for _ in range(20)]
        result = compute_d_score(trials)
        assert result["d_score"] == pytest.approx(0.0, abs=0.01)

    def test_result_contains_required_keys(self):
        result = compute_d_score(self._symmetric_trials())
        for key in ["d_score", "mean_rt_block3", "mean_rt_block4",
                    "mean_rt_block6", "mean_rt_block7",
                    "pooled_sd_blocks3_6", "pooled_sd_blocks4_7", "error_rate"]:
            assert key in result

    def test_error_rate_calculated(self):
        # 4 blocks × 20 trials = 80 total; 1 error → error_rate = 1/80
        trials = [make_trial(b, 700) for b in [3, 4, 6, 7] for _ in range(20)]
        trials[0] = make_trial(3, 700, correct=False)  # replace one with an error
        result = compute_d_score(trials)
        assert result["error_rate"] == pytest.approx(1 / 80, rel=0.01)


# ── interpretation ─────────────────────────────────────────────────────────────

class TestInterpretDScore:
    @pytest.mark.parametrize("d, expected", [
        (0.05,  "little to no"),
        (0.20,  "slight"),
        (0.50,  "moderate"),
        (0.80,  "strong"),
        (-0.80, "strong"),   # magnitude-based
    ])
    def test_thresholds(self, d, expected):
        assert expected in interpret_d_score(d)
