from __future__ import annotations
"""
Rough Set Information System

Universe U   = set of TelemetryWindows (one per 5-second kinematic window)
Attributes B = {tortuosity, tau_deviation, stutter_count, velocity_variance,
                acceleration_variance, time_on_task, w_fatigue, s_bias}
Concept X    = {u ∈ U : u.label == HIGH_RISK}

Two objects x, y are B-indiscernible (IND_B) if their discretized attribute
vectors are identical.  This partitions U into equivalence classes [x]_B.

Lower Approximation  B*(X)  = {x ∈ U : [x]_B ⊆ X}           → Positive Region
Upper Approximation  B^*(X) = {x ∈ U : [x]_B ∩ X ≠ ∅}
Boundary Region      BN(X)  = B^*(X) − B*(X)                  → Gray Zone

References
----------
Pawlak, Z. (1982). Rough sets. International Journal of Computer &
  Information Sciences, 11(5), 341–356.
Grzymala-Busse, J.W. (1992). LERS — A system for learning from examples
  based on rough sets.
"""

import bisect
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────────────────────
# Attribute ordering (determines position in AttrVector tuple)
# ─────────────────────────────────────────────────────────────────────────────

ATTRIBUTES: list[str] = [
    "tortuosity",
    "tau_deviation",
    "stutter_count",
    "velocity_variance",
    "acceleration_variance",
    "time_on_task",
    "w_fatigue",
    "s_bias",
]

# Discretization cut-points.
# Value v goes into bin i  ⟺  CUT_POINTS[attr][i-1] ≤ v < CUT_POINTS[attr][i]
# bin 0  →  v < CUT_POINTS[attr][0]
# bin n  →  v ≥ CUT_POINTS[attr][n-1]
CUT_POINTS: dict[str, list[float]] = {
    "tortuosity":            [1.2,  1.5,  2.0],        # 4 bins
    "tau_deviation":         [0.0,  1.0,  2.0],        # 4 bins (negative = below baseline)
    "stutter_count":         [0.5,  1.5,  2.5],        # 4 bins  0 | 1 | 2 | 3+
    "velocity_variance":     [50.0, 200.0, 500.0],     # 4 bins
    "acceleration_variance": [20.0, 80.0,  200.0],     # 4 bins
    "time_on_task":          [2.0,  4.0,   6.0],       # 4 bins (seconds)
    "w_fatigue":             [0.25, 0.50,  0.75],      # 4 bins
    "s_bias":                [-0.35, 0.35, 0.65],      # 4 bins  (IAT D-score)
}

# Human-readable labels for each bin (used in rule text generation)
BIN_LABELS: dict[str, list[str]] = {
    "tortuosity":            ["baseline (< 1.2)",    "slight (1.2–1.5)",    "elevated (1.5–2.0)",  "severe (≥ 2.0)"],
    "tau_deviation":         ["below baseline",       "within 1σ",           "1–2σ above baseline", "> 2σ above baseline"],
    "stutter_count":         ["0 stutters",           "1 stutter",           "2 stutters",          "3+ stutters"],
    "velocity_variance":     ["low (< 50)",           "moderate (50–200)",   "high (200–500)",      "very high (≥ 500)"],
    "acceleration_variance": ["smooth (< 20)",        "moderate jerk",       "high jerk",           "severe jerk (≥ 200)"],
    "time_on_task":          ["< 2 s",                "2–4 s",               "4–6 s",               "> 6 s"],
    "w_fatigue":             ["rested (< 0.25)",      "mild (0.25–0.50)",    "moderate (0.50–0.75)","severe (≥ 0.75)"],
    "s_bias":                ["counter-stereo (< −0.35)", "neutral (±0.35)", "slight bias (0.35–0.65)", "strong bias (≥ 0.65)"],
}

AttrVector = tuple[int, ...]  # one bin index per attribute, len == len(ATTRIBUTES)

HIGH_RISK = 1
LOW_RISK  = 0


# ─────────────────────────────────────────────────────────────────────────────
# Discretisation
# ─────────────────────────────────────────────────────────────────────────────

def discretize(attrs: dict[str, float]) -> AttrVector:
    """
    Maps a raw attribute dict to a discretized AttrVector using bisect.

    bisect_right(cuts, v) returns the number of cut-points strictly less than v,
    which is exactly the bin index we want.
    """
    return tuple(
        bisect.bisect_right(CUT_POINTS[attr], attrs.get(attr, 0.0))
        for attr in ATTRIBUTES
    )


def bootstrap_label(attrs: dict[str, float]) -> int:
    """
    Assigns a preliminary label before outcome data is available.

    Criteria (conservatively derived from clinical literature on fatigue
    and implicit bias affecting decision-making):
      - tau_deviation > 2σ  AND  stutter_count ≥ 2  → high_risk
      - w_fatigue > 0.60    AND  tau_deviation > 1.5 → high_risk
      - tau_deviation > 3σ  (extreme motor deviation alone) → high_risk
    """
    tau_dev  = attrs.get("tau_deviation", 0.0)
    stutters = attrs.get("stutter_count", 0)
    fatigue  = attrs.get("w_fatigue", 0.0)

    if tau_dev > 1.5 and stutters >= 1:
        return HIGH_RISK
    if fatigue > 0.45 and tau_dev > 1.0:
        return HIGH_RISK
    if tau_dev > 2.5:
        return HIGH_RISK
    return LOW_RISK


# ─────────────────────────────────────────────────────────────────────────────
# Information system objects
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LabeledObject:
    """One row in the Rough Set information system."""
    window_id:    int
    case_id:      int | None       # which triage case was active when this window was recorded
    attrs:        dict[str, float] # raw kinematic values
    discretized:  AttrVector
    label:        int              # HIGH_RISK | LOW_RISK
    label_source: str              # "bootstrap" | "outcome" | "adherence"


@dataclass
class InducedRule:
    """One decision rule extracted from the information system."""
    conditions:  list[str]  # ["tortuosity = elevated (1.5–2.0)", ...]
    consequent:  str        # "high_risk" | "boundary_risk"
    certainty:   float      # |class ∩ X| / |class|
    support:     int        # number of objects covered

    def to_text(self) -> str:
        cond = " AND ".join(self.conditions)
        return f"IF {cond} THEN {self.consequent} [certainty: {self.certainty:.2f}, support: {self.support}]"


# ─────────────────────────────────────────────────────────────────────────────
# Core information system
# ─────────────────────────────────────────────────────────────────────────────

class InformationSystem:
    """
    Per-session Rough Set information system.

    Incrementally builds the universe U and equivalence class partition
    as new TelemetryWindows arrive.  Supports retrospective label updates
    once case decision outcomes are known.
    """

    MIN_OBJECTS_FOR_RST = 6  # minimum rows before RST replaces the heuristic

    def __init__(self, session_id: int) -> None:
        self.session_id = session_id
        self._objects:  list[LabeledObject]          = []
        # AttrVector → list of object indices
        self._classes:  dict[AttrVector, list[int]]  = {}
        # case_id → list of object indices (for retrospective labelling)
        self._case_map: dict[int, list[int]]         = {}
        # Pre-induced rules from external dataset (warm-start explanations)
        self._bootstrap_rules: list[InducedRule]     = []

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_object(self, obj: LabeledObject) -> None:
        idx = len(self._objects)
        self._objects.append(obj)

        # Equivalence class index
        self._classes.setdefault(obj.discretized, []).append(idx)

        # Case map
        if obj.case_id is not None:
            self._case_map.setdefault(obj.case_id, []).append(idx)

    def seed(self, objects: list[LabeledObject]) -> None:
        """Pre-populates IS with bootstrap training objects from an external dataset."""
        if self._objects:
            raise RuntimeError(
                "seed() called on a non-empty InformationSystem — seed before adding real windows"
            )
        for obj in objects:
            self.add_object(obj)

    def set_bootstrap_rules(self, rules: list[InducedRule]) -> None:
        """Stores pre-induced rules as the cold-start fallback for the explanation modal."""
        self._bootstrap_rules = rules

    def get_rules(self, certainty_threshold: float) -> list[InducedRule]:
        """
        Returns live session-induced rules when the IS is large enough,
        otherwise falls back to the pre-induced bootstrap rules.

        This ensures the hard nudge modal always has something to show.
        """
        if self.size >= self.MIN_OBJECTS_FOR_RST:
            live = self.induce_rules(certainty_threshold)
            if live:
                return live
        return self._bootstrap_rules

    def update_labels_for_case(
        self,
        case_id: int,
        is_correct: bool,
        source: str = "outcome",
    ) -> None:
        """
        Retrospectively relabels all windows recorded during `case_id`.

        Incorrect decision → windows during that case were high_risk.
        Correct decision   → windows were low_risk (confirmed by outcome).

        This replaces the bootstrap label with ground-truth outcome data.
        """
        label = HIGH_RISK if not is_correct else LOW_RISK
        for idx in self._case_map.get(case_id, []):
            self._objects[idx].label = label
            self._objects[idx].label_source = source

    def update_label_by_window(
        self,
        window_id: int,
        label: int,
        source: str = "adherence",
    ) -> None:
        """Update the label of a single window (e.g., after nudge adherence signal)."""
        for obj in self._objects:
            if obj.window_id == window_id:
                obj.label = label
                obj.label_source = source
                return

    # ── Classification ────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self._objects)

    def _high_risk_set(self) -> set[int]:
        return {i for i, obj in enumerate(self._objects) if obj.label == HIGH_RISK}

    def classify(self, vec: AttrVector) -> tuple[str, float]:
        """
        RST-based classification of a new attribute vector.

        Returns (region, certainty) where certainty = |[x]_B ∩ X| / |[x]_B|.

        Falls back to "insufficient_data" when U is too small for reliable
        equivalence class statistics — the caller then uses the heuristic.
        """
        if self.size < self.MIN_OBJECTS_FOR_RST:
            return "insufficient_data", 0.0

        high_risk = self._high_risk_set()
        class_indices = self._classes.get(vec)

        if class_indices is None:
            return self._nearest_neighbour_classify(vec, high_risk)

        class_set = set(class_indices)
        overlap   = class_set & high_risk
        certainty = len(overlap) / len(class_set)

        if certainty >= 1.0:
            return "positive_region", certainty
        elif certainty > 0.0:
            return "boundary_region", certainty
        else:
            return "negative_region", 0.0

    def _nearest_neighbour_classify(
        self,
        vec: AttrVector,
        high_risk: set[int],
    ) -> tuple[str, float]:
        """
        For unseen attribute combinations, find the nearest equivalence class
        using Hamming distance on the discretized vectors, then use its
        certainty as a proxy.
        """
        if not self._classes:
            return "negative_region", 0.0

        best_dist      = len(ATTRIBUTES) + 1
        best_certainty = 0.0
        best_region    = "negative_region"

        for class_vec, indices in self._classes.items():
            dist = sum(a != b for a, b in zip(vec, class_vec))
            if dist < best_dist:
                best_dist      = dist
                class_set      = set(indices)
                overlap        = class_set & high_risk
                best_certainty = len(overlap) / len(class_set)
                if best_certainty >= 1.0:
                    best_region = "positive_region"
                elif best_certainty > 0.0:
                    best_region = "boundary_region"
                else:
                    best_region = "negative_region"

        return best_region, best_certainty

    # ── Rule induction ────────────────────────────────────────────────────────

    def induce_rules(self, certainty_threshold: float = 0.5) -> list[InducedRule]:
        """
        Induces decision rules using a LERS-inspired approach.

        For each equivalence class with certainty ≥ threshold:
          1. Build the full attribute-value antecedent
          2. Reduce redundant conditions (attribute reduction)
          3. Emit an InducedRule with certainty and support

        Only classes with at least one high_risk member are considered.
        Returns rules sorted by certainty desc, then support desc.
        """
        if self.size < self.MIN_OBJECTS_FOR_RST:
            return []

        high_risk = self._high_risk_set()
        rules:    list[InducedRule] = []
        seen_conditions: set[frozenset] = set()  # dedup after reduction

        for class_vec, indices in self._classes.items():
            class_set = set(indices)
            overlap   = class_set & high_risk

            if not overlap:
                continue

            certainty = len(overlap) / len(class_set)
            if certainty < certainty_threshold:
                continue

            support    = len(overlap)
            consequent = "high_risk" if certainty >= 1.0 else "boundary_risk"

            # Full antecedent
            full_conditions = self._vector_to_conditions(class_vec)

            # Attribute reduction
            reduced = self._reduce(full_conditions, class_vec, high_risk, certainty)

            key = frozenset((c["attr"], c["bin"]) for c in reduced)
            if key in seen_conditions:
                continue
            seen_conditions.add(key)

            rules.append(InducedRule(
                conditions=[c["text"] for c in reduced],
                consequent=consequent,
                certainty=round(certainty, 3),
                support=support,
            ))

        return sorted(rules, key=lambda r: (-r.certainty, -r.support))

    def _vector_to_conditions(self, vec: AttrVector) -> list[dict]:
        result = []
        for attr, bin_idx in zip(ATTRIBUTES, vec):
            label = BIN_LABELS[attr][bin_idx] if bin_idx < len(BIN_LABELS[attr]) else f"bin {bin_idx}"
            result.append({"attr": attr, "bin": bin_idx, "text": f"{attr} = {label}"})
        return result

    def _reduce(
        self,
        conditions: list[dict],
        vec: AttrVector,
        high_risk: set[int],
        original_certainty: float,
        tolerance: float = 0.02,
    ) -> list[dict]:
        """
        Greedy attribute reduction.

        Attempts to drop each condition; keeps the drop if the certainty of
        the resulting generalised rule does not fall below
        (original_certainty − tolerance).
        """
        reduced = list(conditions)
        i = 0
        while i < len(reduced):
            without   = reduced[:i] + reduced[i + 1:]
            kept_pos  = [ATTRIBUTES.index(c["attr"]) for c in without]

            if not kept_pos:
                break  # never drop all conditions

            # Objects matching the projected vector
            proj_target = tuple(vec[p] for p in kept_pos)
            matching = [
                idx for idx, obj in enumerate(self._objects)
                if tuple(obj.discretized[p] for p in kept_pos) == proj_target
            ]

            if not matching:
                i += 1
                continue

            overlap     = set(matching) & high_risk
            new_cert    = len(overlap) / len(matching)

            if new_cert >= original_certainty - tolerance:
                reduced = without  # drop the condition
            else:
                i += 1

        return reduced


# ─────────────────────────────────────────────────────────────────────────────
# Registry (singleton)
# ─────────────────────────────────────────────────────────────────────────────

class InformationSystemRegistry:
    def __init__(self) -> None:
        self._systems:          dict[int, InformationSystem] = {}
        # Set by dataset_loader.initialise_from_datasets() at startup
        self._seed_objects:     list[LabeledObject]           = []
        self._bootstrap_rules:  list[InducedRule]             = []

    def get_or_create(self, session_id: int) -> InformationSystem:
        if session_id not in self._systems:
            is_sys = InformationSystem(session_id)
            if self._seed_objects:
                is_sys.seed(self._seed_objects)
            if self._bootstrap_rules:
                is_sys.set_bootstrap_rules(self._bootstrap_rules)
            self._systems[session_id] = is_sys
        return self._systems[session_id]

    def remove(self, session_id: int) -> None:
        self._systems.pop(session_id, None)


is_registry = InformationSystemRegistry()
