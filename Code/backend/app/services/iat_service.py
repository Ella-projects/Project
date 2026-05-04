from __future__ import annotations
"""
IAT Administration Service

Implements the Implicit Association Test using the standard 7-block structure
(Greenwald et al., 2003) with D-score computation.

The IAT dynamically generates stimuli from configurable category/attribute pools.
In this implementation, the domain is clinical triage: the test measures implicit
associations between demographic categories and clinical severity judgements.

Block structure:
  Block 1 (practice): Target discrimination
  Block 2 (practice): Attribute discrimination
  Block 3 (test):     Compatible mapping  — 20 trials
  Block 4 (test):     Compatible mapping  — 40 trials
  Block 5 (practice): Reversed target
  Block 6 (test):     Incompatible mapping — 20 trials
  Block 7 (test):     Incompatible mapping — 40 trials

D-score = ((mean_RT_blocks4+7 - mean_RT_blocks3+6) / pooled_SD)
"""

import random
from dataclasses import dataclass

from app.core.config import settings
from app.models.schemas.profile import IATSummary


# ---------------------------------------------------------------------------
# Stimulus pools — replace/extend with domain-specific content
# ---------------------------------------------------------------------------

# Category keys — names are the clinical concepts they represent,
# used as labels in the UI and stored in the database.
# "Elderly" / "Young" are the demographic target groups.
# "High Acuity" / "Low Acuity" are the clinical severity attributes.

ELDERLY_WORDS: list[str] = [
    "Elderly", "Senior", "Aged", "Old", "Geriatric",
]

YOUNG_WORDS: list[str] = [
    "Young", "Youth", "Adolescent", "Juvenile", "Child",
]

MALE_WORDS: list[str] = [
    "Male", "Man", "Masculine", "Sir", "He",
]

FEMALE_WORDS: list[str] = [
    "Female", "Woman", "Feminine", "Ma'am", "She",
]

WHITE_WORDS: list[str] = [
    "White", "Caucasian", "European", "Anglo", "Western",
]

BLACK_WORDS: list[str] = [
    "Black", "African", "Caribbean", "Afro", "Melanin",
]

HIGH_ACUITY_WORDS: list[str] = [
    "Severe", "Critical", "Urgent", "Priority", "Immediate",
]

LOW_ACUITY_WORDS: list[str] = [
    "Mild", "Stable", "Minor", "Routine", "Deferred",
]

# Demographic target pair per bias type — (group_a, group_b)
_DEMOGRAPHIC_PAIR: dict[str, tuple[str, str]] = {
    "age":    ("Elderly", "Young"),
    "gender": ("Male",    "Female"),
    "race":   ("White",   "Black"),
}


@dataclass
class IATStimulus:
    word: str
    category: str  # "Elderly" | "Young" | "High Acuity" | "Low Acuity"
    correct_key: str  # "e" | "i"
    block_number: int
    trial_number: int
    is_practice: bool


@dataclass
class BlockSpec:
    block_number: int
    is_practice: bool
    trial_count: int
    # Mapping: key → list of categories assigned to that key
    left_categories: list[str]  # key "e"
    right_categories: list[str]  # key "i"


def build_block_specs(
    practice_count: int,
    test_count_short: int,
    test_count_long: int,
    bias_type: str = "age",
) -> list[BlockSpec]:
    """
    Returns the 7-block IAT structure for the given bias dimension.

    bias_type controls which demographic pair is used:
      "age"    → Elderly / Young
      "gender" → Male / Female
      "race"   → White / Black

    The clinical severity attributes (High Acuity / Low Acuity) are the
    same across all three dimensions.
    """
    if bias_type not in _DEMOGRAPHIC_PAIR:
        raise ValueError(f"Unknown bias_type: {bias_type!r}")

    group_a, group_b = _DEMOGRAPHIC_PAIR[bias_type]
    return [
        BlockSpec(1, True,  practice_count,   [group_a],                          [group_b]),
        BlockSpec(2, True,  practice_count,   ["High Acuity"],                    ["Low Acuity"]),
        BlockSpec(3, False, test_count_short,  [group_a, "High Acuity"],          [group_b, "Low Acuity"]),
        BlockSpec(4, False, test_count_long,   [group_a, "High Acuity"],          [group_b, "Low Acuity"]),
        BlockSpec(5, True,  practice_count,   [group_b],                          [group_a]),
        BlockSpec(6, False, test_count_short,  [group_b, "High Acuity"],          [group_a, "Low Acuity"]),
        BlockSpec(7, False, test_count_long,   [group_b, "High Acuity"],          [group_a, "Low Acuity"]),
    ]


def generate_stimuli_for_block(spec: BlockSpec) -> list[IATStimulus]:
    """
    Randomly samples stimuli for a block, ensuring balanced category representation.
    """
    all_categories: list[tuple[str, list[str], str]] = []

    for cat in spec.left_categories:
        pool = _pool_for(cat)
        all_categories.append((cat, pool, "e"))

    for cat in spec.right_categories:
        pool = _pool_for(cat)
        all_categories.append((cat, pool, "i"))

    stimuli: list[IATStimulus] = []
    trials_per_cat = max(1, spec.trial_count // len(all_categories))

    for cat, pool, key in all_categories:
        words = random.choices(pool, k=trials_per_cat)
        for i, word in enumerate(words):
            stimuli.append(
                IATStimulus(
                    word=word,
                    category=cat,
                    correct_key=key,
                    block_number=spec.block_number,
                    trial_number=len(stimuli) + i + 1,
                    is_practice=spec.is_practice,
                )
            )

    random.shuffle(stimuli)
    for i, s in enumerate(stimuli):
        s.trial_number = i + 1

    return stimuli


def _pool_for(category: str) -> list[str]:
    return {
        "Elderly":     ELDERLY_WORDS,
        "Young":       YOUNG_WORDS,
        "Male":        MALE_WORDS,
        "Female":      FEMALE_WORDS,
        "White":       WHITE_WORDS,
        "Black":       BLACK_WORDS,
        "High Acuity": HIGH_ACUITY_WORDS,
        "Low Acuity":  LOW_ACUITY_WORDS,
    }[category]


def compute_d_score(
    trials: list[dict],  # dicts with keys: block_number, reaction_time_ms, is_correct, is_practice
) -> dict:
    """
    Computes the Greenwald (2003) D-score.

    Steps:
      1. Eliminate trials with RT < 300ms
      2. Replace error RT with block mean + 600ms penalty
      3. Compute mean RT for blocks 3, 4, 6, 7
      4. Compute pooled SDs for (3,6) and (4,7)
      5. D = ((mean46 - mean37) + (mean47 - mean36)) / 2 ... see standard formula
         Simplified: D = mean of two sub-D scores

    Returns a dict with d_score and intermediate values.
    """
    def _filter_block(block_num: int) -> list[float]:
        rts = []
        for t in trials:
            if t["block_number"] != block_num or t.get("is_practice"):
                continue
            rt = t["reaction_time_ms"]
            if rt < settings.iat_min_rt_ms:
                continue
            if not t.get("is_correct", True):
                # Error penalty: block mean + 600ms (applied after block mean computed)
                rt = None  # placeholder — resolved in second pass
            if rt is not None:
                rts.append(float(rt))
        return rts

    def _apply_error_penalty(block_num: int, block_mean: float) -> list[float]:
        rts = []
        for t in trials:
            if t["block_number"] != block_num or t.get("is_practice"):
                continue
            rt = float(t["reaction_time_ms"])
            if rt < settings.iat_min_rt_ms:
                continue
            if not t.get("is_correct", True):
                rt = block_mean + settings.iat_fast_response_penalty_ms
            rts.append(rt)
        return rts

    import numpy as np

    # First pass — compute block means without error penalty
    raw: dict[int, list[float]] = {b: _filter_block(b) for b in [3, 4, 6, 7]}
    raw_means = {b: float(np.mean(v)) if v else 0.0 for b, v in raw.items()}

    # Second pass — apply error penalty and recompute
    penalized: dict[int, list[float]] = {
        b: _apply_error_penalty(b, raw_means[b]) for b in [3, 4, 6, 7]
    }
    means = {b: float(np.mean(v)) if v else 0.0 for b, v in penalized.items()}

    # Pooled SDs
    def _pooled_sd(b1: int, b2: int) -> float:
        combined = penalized[b1] + penalized[b2]
        return float(np.std(combined, ddof=1)) if len(combined) > 1 else 1.0

    sd_36 = _pooled_sd(3, 6)
    sd_47 = _pooled_sd(4, 7)

    d1 = (means[6] - means[3]) / sd_36 if sd_36 > 0 else 0.0
    d2 = (means[7] - means[4]) / sd_47 if sd_47 > 0 else 0.0
    d_score = (d1 + d2) / 2.0

    error_trials = sum(1 for t in trials if not t.get("is_correct", True) and not t.get("is_practice"))
    total_trials = sum(1 for t in trials if not t.get("is_practice"))
    error_rate = error_trials / total_trials if total_trials > 0 else 0.0

    return {
        "d_score": round(d_score, 4),
        "mean_rt_block3": round(means[3], 2),
        "mean_rt_block4": round(means[4], 2),
        "mean_rt_block6": round(means[6], 2),
        "mean_rt_block7": round(means[7], 2),
        "pooled_sd_blocks3_6": round(sd_36, 2),
        "pooled_sd_blocks4_7": round(sd_47, 2),
        "error_rate": round(error_rate, 4),
    }


def interpret_d_score(d_score: float) -> str:
    """
    Maps D-score magnitude to an interpretation string.
    Thresholds per Greenwald et al. (2003) convention.
    """
    abs_d = abs(d_score)
    if abs_d < 0.15:
        return "little to no implicit association"
    elif abs_d < 0.35:
        return "slight implicit association"
    elif abs_d < 0.65:
        return "moderate implicit association"
    else:
        return "strong implicit association"
