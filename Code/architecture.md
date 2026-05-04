# AdaptiveUI — System Architecture

## Overview

AdaptiveUI is a closed-loop clinical decision-support system that measures implicit bias across three demographic dimensions (age, gender, race) via sequential Implicit Association Tests, calibrates individual motor baselines, then delivers adaptive nudges during triage decision-making based on a Rough Set Theory classifier.

---

## Full Architecture Diagram

```mermaid
flowchart TD

    %% ── External datasets ────────────────────────────────────────────────
    subgraph EXT ["External Datasets  (read once at startup)"]
        DS_AGE["Age IAT CSV\n(2 GB · 2002-2021)\nD_biep.Young_Good_all"]
        DS_GEN["Gender IAT CSV\n(1.9 GB · 2005-2020)\nD_biep.Male_Career_all"]
        DS_RACE["Race IAT CSV\n(639 MB · 2025)\nD_biep.White_Good_all"]
        DS_FAT["Human Decision\nFatigue Dataset\n(1.5 MB)"]
    end

    %% ── Backend startup ──────────────────────────────────────────────────
    subgraph STARTUP ["Startup  (FastAPI lifespan hook)"]
        DL["dataset_loader\ninitialise_from_datasets()"]
        PRIORS["Per-dimension priors\ns_bias_prior_age   = 0.500\ns_bias_prior_gender = 0.373\ns_bias_prior_race  = 0.256"]
        SEEDS["50 × LabeledObject\nIS seed pool\n(fatigue → kinematic mapping)"]
        BRULES["Bootstrap rules\n(pre-induced from seeds)\nJSON cache"]
    end

    DS_AGE & DS_GEN & DS_RACE -->|"pandas read_csv\nusecols + nrows=50k"| DL
    DS_FAT -->|"map cognitive→kinematic\nattrs via formulas"| DL
    DL --> PRIORS & SEEDS & BRULES

    %% ── Frontend ─────────────────────────────────────────────────────────
    subgraph FE ["Frontend  (React 18 + Vite + Zustand)"]
        direction TB
        subgraph FE_PHASES ["Session Phase Flow"]
            direction LR
            P_IAT["IATAdministrator\n① Age IAT\n② Gender IAT\n③ Race IAT\n(each: 7 blocks)"]
            P_CAL["Calibration\n30 s neutral\nmouse task"]
            P_TRIAGE["TriageCase\n+ TelemetryCapture\n(mouse stream)"]
            P_IAT -->|"onComplete"| P_CAL -->|"onComplete"| P_TRIAGE
        end
        STORE["Zustand Store\nsession · user · iatPhase\npendingHardNudge · activeSoftNudge"]
        NUDGE_UI["HardNudge modal\nSoftNudge luminance highlight"]
        WS_HOOK["useWebSocket\n(ws://localhost:8000/ws/telemetry/{id})"]
        API_SVC["apiService\n(REST via Vite proxy /api → :8000)"]
    end

    %% ── REST API ─────────────────────────────────────────────────────────
    subgraph API ["Backend REST  (FastAPI · /api)"]
        direction TB
        R_SESS["/session/start\n/session/end"]
        R_PROF["/profile/{id}\n/profile/{id}/baseline"]
        R_IAT["/iat/blocks/{id}?bias_type=\n/iat/response\n/iat/complete"]
        R_CASES["/cases/next/{id}\n/cases/decision"]
        R_NUDGE["/nudge/acknowledge"]
        R_WS["WebSocket\n/ws/telemetry/{session_id}"]
    end

    API_SVC <-->|"HTTP"| R_SESS & R_PROF & R_IAT & R_CASES & R_NUDGE
    WS_HOOK <-->|"WS frames"| R_WS

    %% ── IAT service ──────────────────────────────────────────────────────
    subgraph IAT_SVC ["IAT Service"]
        BUILD["build_block_specs(bias_type)\nBlock 1-2: practice\nBlocks 3,4: compatible\nBlock 5: reversal\nBlocks 6,7: incompatible"]
        DSCORE["compute_d_score(trials)\nGreenwald 2003 algorithm\nD = (mean_RT_inc − mean_RT_con)\n     ÷ pooled_SD\n(blocks 4+7 vs 3+6)"]
        INTERP["interpret_d_score(D)\n|D| < 0.15 → negligible\n0.15–0.35 → slight\n0.35–0.65 → moderate\n> 0.65 → strong"]
    end

    R_IAT --> BUILD & DSCORE & INTERP

    %% ── Profile service ──────────────────────────────────────────────────
    subgraph PROF_SVC ["Profile Service"]
        UPD_BIAS["update_s_bias(user_id, d_score, bias_type)\nstores s_bias_age / _gender / _race"]
        UPD_BL["compute_and_store_baseline()\nd_score_baseline  = mean τ\nd_score_baseline_std = σ τ"]
    end

    DSCORE -->|"d_score + bias_type"| UPD_BIAS
    R_PROF --> UPD_BL

    %% ── RST / Nudge pipeline ─────────────────────────────────────────────
    subgraph RST_PIPE ["RST Nudge Pipeline  (per kinematic window)"]
        direction TB
        SM["state_monitor\nW_fatigue update\n(exponential weighted τ)"]
        IS["InformationSystem\nEquivalence classes\nPositive / boundary / negative regions"]
        RST_CLS["rough_set\nbuild_nudge_decision()\nclassification: HIGH_RISK / LOW_RISK / UNCERTAIN"]
        RM["risk_model\nP = W_fatigue × max(|s_bias_age|,|s_bias_gender|,|s_bias_race|) / 2\nclamped to [0, 1]"]
        DR["decision_rules\ngenerate_rules()\nexplanation text for modal"]
        ND{"NudgeDecision\nP threshold?"}
        HARD["HardNudgePayload\nrisk_score · evidence rules\nrequires confirmation"]
        SOFT["SoftNudgePayload\nrisk_score · target_field_ids\nluminance_delta · duration_ms"]
    end

    SEEDS -->|"seed() on new session\nvia IS Registry"| IS
    BRULES -->|"set_bootstrap_rules()\nfallback until 6+ live windows"| IS
    R_WS -->|"KinematicWindow\n(tortuosity, τ_dev, stutter_count,\nvelocity_var, accel_var, time_on_task)"| SM
    SM -->|"w_fatigue"| RST_CLS
    IS -->|"get_rules()\nor bootstrap rules"| DR
    RST_CLS --> RM
    RM --> ND
    ND -->|"P ≥ 0.6 &\nis_counter_stereotypical"| HARD
    ND -->|"0.3 ≤ P < 0.6"| SOFT
    DR --> HARD

    HARD & SOFT -->|"WebSocket push"| WS_HOOK
    WS_HOOK --> NUDGE_UI
    NUDGE_UI --> STORE

    %% ── Database ─────────────────────────────────────────────────────────
    subgraph DB ["PostgreSQL"]
        direction LR
        T_USERS[("users\n─────────────\ns_bias_age\ns_bias_gender\ns_bias_race\nd_score_baseline\nd_score_baseline_std")]
        T_SESS[("clinical_sessions\n─────────────\nnudge_order\nw_fatigue\ndelta_acc")]
        T_IAT_T[("iat_trials\n─────────────\nbias_type\nblock_number\nreaction_time_ms\nis_correct")]
        T_IAT_R[("iat_results\n─────────────\nbias_type\nd_score\nerror_rate")]
        T_CASES[("triage_cases\n─────────────\npatient_label\ncorrect_decision\nis_counter_stereotypical")]
        T_DEC[("case_decisions\n─────────────\ndecision\nnudge_fired\npre_nudge_decision")]
        T_TEL[("telemetry_windows\n─────────────\ntortuosity · tau_dev\nrisk_score\nrs_classification")]
    end

    UPD_BIAS --> T_USERS
    UPD_BL   --> T_USERS
    R_SESS   --> T_SESS
    R_IAT    --> T_IAT_T & T_IAT_R
    R_CASES  --> T_DEC
    R_WS     --> T_TEL
    T_USERS  -->|"s_bias_{age,gender,race}\nd_score_baseline"| RST_PIPE

    %% ── Alembic ──────────────────────────────────────────────────────────
    MIGR["Alembic migrations\na1b2c3d4 → b2c3d4e5\n→ d5e6f7a8"]
    MIGR -.->|"schema"| DB

    %% ── Colour coding ────────────────────────────────────────────────────
    style EXT      fill:#fef9c3,stroke:#ca8a04
    style STARTUP  fill:#fef9c3,stroke:#ca8a04
    style FE       fill:#dbeafe,stroke:#2563eb
    style FE_PHASES fill:#eff6ff,stroke:#93c5fd
    style API      fill:#f0fdf4,stroke:#16a34a
    style IAT_SVC  fill:#f0fdf4,stroke:#16a34a
    style PROF_SVC fill:#f0fdf4,stroke:#16a34a
    style RST_PIPE fill:#fdf4ff,stroke:#9333ea
    style DB       fill:#fff7ed,stroke:#ea580c
```

---

## Data Flow Summary

| Phase | Trigger | Key path |
|-------|---------|----------|
| **Startup** | Server boot | Datasets → `dataset_loader` → priors + IS seed pool + bootstrap rules |
| **Boot** | App load | `GET /profile` + `POST /session/start` → Zustand store |
| **Age IAT** | Mount | `GET /iat/blocks?bias_type=age` → 7 blocks → `POST /iat/response` × N → `POST /iat/complete` → `s_bias_age` stored |
| **Gender IAT** | Age complete | Same flow with `bias_type=gender` → `s_bias_gender` stored |
| **Race IAT** | Gender complete | Same flow with `bias_type=race` → `s_bias_race` stored |
| **Calibration** | IAT complete | Mouse movement → `POST /profile/baseline` → `d_score_baseline` stored |
| **Triage** | Calibration complete | Each mouse window → WebSocket → RST pipeline → P computed → nudge pushed back via WebSocket |
| **Nudge** | P threshold crossed | WebSocket hard/soft nudge → frontend modal/highlight → `POST /nudge/acknowledge` |

---

## Risk Model

```
P = W_fatigue × max(|s_bias_age|, |s_bias_gender|, |s_bias_race|) / 2

where:
  W_fatigue ∈ [0, 1]   — exponentially-weighted kinematic fatigue signal
  s_bias_*  ∈ [-2, 2]  — Greenwald D-score per IAT dimension
  P         ∈ [0, 1]   — probability of bias-influenced decision

Hard nudge:  P ≥ 0.6 AND case is_counter_stereotypical
Soft nudge:  0.3 ≤ P < 0.6
```

---

## ML Engine (RST)

The Rough Set Theory engine operates per clinical session:

1. **Cold start** — IS seeded with 50 labelled objects from the fatigue dataset (mapped from cognitive features to kinematic attributes). Bootstrap rules loaded from JSON cache.
2. **Per window** — `LabeledObject` added to IS; equivalence classes recomputed.
3. **Classification** — once IS has ≥ 6 objects, live rule induction replaces bootstrap rules.
4. **Explanation** — `generate_rules()` produces natural-language evidence strings for the hard nudge modal.

Population priors (loaded from Project Implicit data, first 50 k rows):

| Dimension | Prior | Source column |
|-----------|-------|---------------|
| Age | 0.500 | `D_biep.Young_Good_all` |
| Gender | 0.373 | `D_biep.Male_Career_all` |
| Race | 0.256 | `D_biep.White_Good_all` |
