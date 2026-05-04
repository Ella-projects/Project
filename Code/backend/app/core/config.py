from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://aui:aui@localhost:5432/adaptiveui"

    # WebSocket
    ws_telemetry_buffer_size: int = 500

    # Kinematic processing
    window_duration_seconds: float = 5.0
    min_points_per_window: int = 10

    # Rough Set thresholds
    lower_approx_threshold: float = 0.45   # Positive Region boundary (hard nudge)
    boundary_region_threshold: float = 0.25  # Gray Zone lower bound (soft nudge)

    # Risk model
    fatigue_weight_default: float = 1.0

    # IAT
    iat_trial_count: int = 80
    iat_practice_trial_count: int = 20
    iat_min_rt_ms: int = 300
    iat_max_rt_ms: int = 10000
    iat_fast_response_penalty_ms: int = 600  # RT floor for D-score penalty

    # Dataset integration — one CSV per IAT dimension (each must have a `d_score` column)
    implicit_bias_age_dataset_path:    str = ""
    implicit_bias_gender_dataset_path: str = ""
    implicit_bias_race_dataset_path:   str = ""
    fatigue_dataset_path:              str = ""
    bootstrap_rules_cache_path:        str = "bootstrap_rules_cache.json"
    is_seed_max_rows:                  int = 50

    # Per-dimension population priors (overwritten at startup from CSVs when available)
    s_bias_prior_age:    float = 0.35   # age IAT population mean
    s_bias_prior_gender: float = 0.30   # gender IAT population mean
    s_bias_prior_race:   float = 0.40   # race IAT population mean

    class Config:
        env_file = ".env"


settings = Settings()
