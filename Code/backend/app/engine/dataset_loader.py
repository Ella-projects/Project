from __future__ import annotations
"""
Dataset Loader

Bootstraps the RST engine from two external datasets at application startup:

  1. Harvard Project Implicit CSVs (one per bias dimension: age, gender, race)
     → Computes per-dimension population D-score means from the _all variant
       (D_biep.Young_Good_all / D_biep.Male_Career_all / D_biep.White_Good_all).
     → Overwrites settings.s_bias_prior_{age,gender,race} when valid files found.

  2. Human Decision Fatigue Dataset CSV
     → Maps cognitive/behavioural fatigue features to IS kinematic attribute schema.
     → Produces LabeledObject seed rows for the Rough Set Information System.
     → Pre-induces decision rules from those seeds and writes a JSON cache.

All failures are non-fatal — missing or malformed files log a message and fall
through to the hardcoded defaults in config.py.
"""

import json
import logging
import pathlib
import random
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd

from app.core.config import settings
from app.engine.information_system import (
    HIGH_RISK,
    LOW_RISK,
    InducedRule,
    InformationSystem,
    LabeledObject,
    discretize,
)

if TYPE_CHECKING:
    from app.engine.information_system import InformationSystemRegistry

logger = logging.getLogger(__name__)

# Project Implicit D-score column per IAT dimension
_IAT_D_SCORE_COLUMNS = {
    "age":    "D_biep.Young_Good_all",
    "gender": "D_biep.Male_Career_all",
    "race":   "D_biep.White_Good_all",
}

# Required columns in the human decision fatigue dataset
_FATIGUE_REQUIRED_COLS = {
    "Hours_Awake", "Avg_Decision_Time_sec", "Error_Rate",
    "Decision_Fatigue_Score", "Stress_Level_1_10",
    "Cognitive_Load_Score", "Fatigue_Level",
}


# ─────────────────────────────────────────────────────────────────────────────
# Project Implicit prior loader
# ─────────────────────────────────────────────────────────────────────────────

def load_population_prior(csv_path: str, bias_type: str) -> Optional[float]:
    """
    Reads a Project Implicit CSV and returns the mean D-score for the given
    bias dimension.

    The D-score column is looked up from _IAT_D_SCORE_COLUMNS:
      age    → D_biep.Young_Good_all
      gender → D_biep.Male_Career_all
      race   → D_biep.White_Good_all

    Returns None on any failure so the caller falls back to the config default.
    """
    if not csv_path:
        return None

    path = pathlib.Path(csv_path)
    if not path.exists():
        logger.info("Population prior CSV not found: %s", csv_path)
        return None

    d_col = _IAT_D_SCORE_COLUMNS.get(bias_type)
    if d_col is None:
        logger.warning("Unknown bias_type %r — cannot load prior", bias_type)
        return None

    # Read only the target column from the first 50 k rows — the mean of a
    # 50 k sample is statistically equivalent to the full-file mean (SEM < 0.001
    # for typical IAT data) and takes milliseconds even on 2 GB files.
    _SAMPLE_ROWS = 50_000
    try:
        df = pd.read_csv(
            path,
            usecols=[d_col],
            nrows=_SAMPLE_ROWS,
            encoding="utf-8-sig",
            on_bad_lines="skip",
        )
    except ValueError:
        # usecols raises ValueError when the column is absent
        # Peek at the actual header to produce a useful log message
        try:
            header = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns.tolist()
        except Exception:
            header = []
        logger.warning(
            "Column '%s' not found in %s (found: %s…)",
            d_col, csv_path, header[:8],
        )
        return None
    except OSError as exc:
        logger.warning("Could not open %s: %s", csv_path, exc)
        return None

    series = pd.to_numeric(df[d_col], errors="coerce")
    scores = series[series.abs() <= 3.0].dropna()

    if len(scores) < 10:
        logger.warning(
            "Only %d valid rows in %s — ignoring", len(scores), csv_path
        )
        return None

    mean = float(scores.mean())
    logger.info(
        "Prior [%s] loaded from %s: mean=%.4f  (n=%d, sample=%d)",
        bias_type, csv_path, mean, len(scores), _SAMPLE_ROWS,
    )
    return mean


# ─────────────────────────────────────────────────────────────────────────────
# Fatigue dataset → IS attribute mapping
# ─────────────────────────────────────────────────────────────────────────────

def _map_fatigue_row_to_attrs(row: dict, s_bias_fallback: float) -> dict[str, float]:
    """
    Converts one row of the human decision fatigue dataset to the 8-attribute
    schema used by the Rough Set Information System.

    Mapping is grounded in the fatigue–motor performance literature:
    elevated cognitive fatigue manifests as increased mouse tortuosity,
    higher kinematic variance, and greater temporal deviation from baseline.

    Source columns → IS attributes:
      Decision_Fatigue_Score / 100          → w_fatigue       [0, 1]
      w_fatigue × 1.2 + hours_factor        → tortuosity      [1.0, ~2.5]
      w_fatigue × 2.5 + hours_factor        → tau_deviation   [0, ~3]
      error_rate × 15 + w_fatigue × 1.5     → stutter_count   [0, 3]
      w_fatigue × 400 + cog_load × 10       → velocity_variance
      w_fatigue × 150 + stress × 5          → acceleration_variance
      Avg_Decision_Time_sec                 → time_on_task    [0.5, 6.8]
      s_bias_fallback                       → s_bias
    """
    hours        = float(row["Hours_Awake"])
    avg_time     = float(row["Avg_Decision_Time_sec"])
    error_rate   = float(row["Error_Rate"])
    fatigue_score = float(row["Decision_Fatigue_Score"])
    stress       = float(row["Stress_Level_1_10"])
    cog_load     = float(row["Cognitive_Load_Score"])

    w_fatigue = fatigue_score / 100.0
    hours_factor = hours / 17.0  # normalise to [0, 1]

    tortuosity            = 1.0 + w_fatigue * 1.2 + hours_factor * 0.4
    tau_deviation         = w_fatigue * 2.5 + hours_factor * 0.5
    stutter_count         = min(3.0, error_rate * 15.0 + w_fatigue * 1.5)
    velocity_variance     = w_fatigue * 400.0 + cog_load * 10.0
    acceleration_variance = w_fatigue * 150.0 + stress * 5.0
    time_on_task          = avg_time

    return {
        "tortuosity":            tortuosity,
        "tau_deviation":         tau_deviation,
        "stutter_count":         stutter_count,
        "velocity_variance":     velocity_variance,
        "acceleration_variance": acceleration_variance,
        "time_on_task":          time_on_task,
        "w_fatigue":             w_fatigue,
        "s_bias":                s_bias_fallback,
    }


def _fatigue_label(row: dict) -> int:
    """HIGH_RISK when Fatigue_Level is 'High', LOW_RISK otherwise."""
    return HIGH_RISK if row.get("Fatigue_Level", "").strip() == "High" else LOW_RISK


# ─────────────────────────────────────────────────────────────────────────────
# Fatigue seed object loader
# ─────────────────────────────────────────────────────────────────────────────

def load_fatigue_seed_objects(
    csv_path: str,
    max_rows: int = 50,
    s_bias_fallback: float = 0.40,
) -> list[LabeledObject]:
    """
    Reads the human decision fatigue CSV and returns LabeledObjects for IS seeding.

    Each row is mapped to IS kinematic attributes via _map_fatigue_row_to_attrs,
    then discretized and labelled (High fatigue → HIGH_RISK, else LOW_RISK).

    Seed objects use negative window_ids (-(i+1)) so they never collide with
    real auto-increment TelemetryWindow ids.  case_id = None ensures they are
    never retrospectively relabelled by outcome data.
    """
    if not csv_path:
        return []

    path = pathlib.Path(csv_path)
    if not path.exists():
        logger.info("Fatigue seed CSV not found: %s", csv_path)
        return []

    objects: list[LabeledObject] = []
    skipped = 0

    # Read only the required columns and enough rows to fill max_rows after
    # dropping any malformed lines (read 4× max_rows as a safe over-sample).
    read_limit = max(max_rows * 4, 200)
    try:
        df = pd.read_csv(
            path,
            usecols=list(_FATIGUE_REQUIRED_COLS),
            nrows=read_limit,
            encoding="utf-8-sig",
            on_bad_lines="skip",
        )
    except ValueError as exc:
        # Missing required column
        try:
            header = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns.tolist()
        except Exception:
            header = []
        missing = _FATIGUE_REQUIRED_COLS - set(header)
        logger.error(
            "Fatigue CSV %s is missing required columns: %s", csv_path, sorted(missing)
        )
        return []
    except OSError as exc:
        logger.warning("Could not open fatigue CSV %s: %s", csv_path, exc)
        return []

    for i, row in df.iterrows():
        try:
            row_dict = row.to_dict()
            attrs = _map_fatigue_row_to_attrs(row_dict, s_bias_fallback)
            label = _fatigue_label(row_dict)
            objects.append(LabeledObject(
                window_id=-(len(objects) + 1),
                case_id=None,
                attrs=attrs,
                discretized=discretize(attrs),
                label=label,
                label_source="bootstrap",
            ))
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug("Skipping row %d in fatigue CSV: %s", i, exc)
            skipped += 1

    if skipped:
        logger.debug("Skipped %d malformed rows in %s", skipped, csv_path)

    # Reproducible shuffle then cap
    random.seed(42)
    random.shuffle(objects)
    objects = objects[:max_rows]

    logger.info(
        "Fatigue seed objects loaded: %d (label split: %d high-risk / %d low-risk)",
        len(objects),
        sum(1 for o in objects if o.label == HIGH_RISK),
        sum(1 for o in objects if o.label == LOW_RISK),
    )
    return objects


# ─────────────────────────────────────────────────────────────────────────────
# Rule induction + JSON cache
# ─────────────────────────────────────────────────────────────────────────────

def induce_and_cache_rules(
    seed_objects: list[LabeledObject],
    cache_path: str,
    certainty_threshold: float,
) -> list[InducedRule]:
    """
    Builds a temporary InformationSystem from seed_objects, induces rules,
    writes them to a JSON cache, and returns the rule list.

    The temporary IS is discarded — never placed in the registry.
    """
    rules: list[InducedRule] = []

    if seed_objects:
        temp_is = InformationSystem(session_id=-1)
        for obj in seed_objects:
            temp_is.add_object(obj)
        rules = temp_is.induce_rules(certainty_threshold)

    try:
        cache = pathlib.Path(cache_path)
        payload = [
            {
                "conditions": r.conditions,
                "consequent": r.consequent,
                "certainty":  r.certainty,
                "support":    r.support,
            }
            for r in rules
        ]
        cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info(
            "Bootstrap rules: %d rule(s) — cache written to %s",
            len(rules), cache_path,
        )
    except OSError as exc:
        logger.warning("Could not write bootstrap rules cache %s: %s", cache_path, exc)

    return rules


def load_cached_rules(cache_path: str) -> list[InducedRule]:
    """Reads the JSON rules cache and reconstructs InducedRule objects."""
    path = pathlib.Path(cache_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [
            InducedRule(
                conditions=entry["conditions"],
                consequent=entry["consequent"],
                certainty=entry["certainty"],
                support=entry["support"],
            )
            for entry in payload
        ]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Could not load bootstrap rules cache %s: %s", cache_path, exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Startup entry point
# ─────────────────────────────────────────────────────────────────────────────

def initialise_from_datasets(registry: "InformationSystemRegistry") -> None:
    """
    Called once at application startup (FastAPI lifespan).

    1. Loads per-dimension population priors from Project Implicit CSVs.
       Overwrites settings.s_bias_prior_{age,gender,race} when valid.

    2. Loads + maps fatigue seed objects → stored on registry._seed_objects.

    3. Induces rules from seed objects → JSON cache → registry._bootstrap_rules.
    """
    # ── 1. Population priors ─────────────────────────────────────────────────
    _dim_paths = {
        "age":    settings.implicit_bias_age_dataset_path,
        "gender": settings.implicit_bias_gender_dataset_path,
        "race":   settings.implicit_bias_race_dataset_path,
    }
    for dim, path in _dim_paths.items():
        prior = load_population_prior(path, dim)
        attr  = f"s_bias_prior_{dim}"
        if prior is not None:
            setattr(settings, attr, prior)
            logger.info("s_bias_prior_%s set to %.4f from dataset", dim, prior)
        else:
            logger.info(
                "s_bias_prior_%s using config default: %.4f",
                dim, getattr(settings, attr),
            )

    # ── 2. Fatigue seed objects ───────────────────────────────────────────────
    composite_prior = max(
        settings.s_bias_prior_age,
        settings.s_bias_prior_gender,
        settings.s_bias_prior_race,
    )
    seed_objects = load_fatigue_seed_objects(
        settings.fatigue_dataset_path,
        max_rows=settings.is_seed_max_rows,
        s_bias_fallback=composite_prior,
    )
    registry._seed_objects = seed_objects

    # ── 3. Rule induction ─────────────────────────────────────────────────────
    try:
        bootstrap_rules = induce_and_cache_rules(
            seed_objects,
            settings.bootstrap_rules_cache_path,
            certainty_threshold=0.5,
        )
    except Exception as exc:
        logger.error("Bootstrap rule induction failed: %s", exc)
        bootstrap_rules = load_cached_rules(settings.bootstrap_rules_cache_path)

    registry._bootstrap_rules = bootstrap_rules
