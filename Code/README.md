# AdaptiveUI — Bias-Aware Adaptive User Interface

A real-time clinical decision support system that detects implicit bias and cognitive fatigue during triage and delivers targeted adaptive nudges to mitigate bias-driven errors.

---

## How It Works

1. The clinician completes three Implicit Association Tests (Age, Gender, Race) before cases begin. D-scores are computed using the Greenwald algorithm and stored per dimension.
2. During triage, mouse movement is continuously streamed and analysed for tortuosity (τ), stutter count, and velocity variance — kinematic proxies for cognitive conflict and fatigue.
3. A Rough Set Theory (RST) engine classifies each kinematic window as LOW\_RISK, UNCERTAIN, or HIGH\_RISK by combining the fatigue coefficient and the max-composite IAT score.
4. Soft nudges (subtle UI shifts) fire at UNCERTAIN; hard nudges (a modal with RST-derived rule explanations) fire at HIGH\_RISK.

---

## Requirements

### System
- Python **3.11+**
- Node.js **20+**
- PostgreSQL **16**
- Docker + Docker Compose (recommended)

### Backend Python packages
| Package | Version |
|---|---|
| fastapi | ≥ 0.115.0 |
| uvicorn | ≥ 0.30.0 |
| sqlalchemy[asyncio] | ≥ 2.0.35 |
| asyncpg | ≥ 0.30.0 |
| alembic | ≥ 1.13.0 |
| pydantic | ≥ 2.9.0 |
| pydantic-settings | ≥ 2.5.0 |
| numpy | ≥ 1.26.4 |
| pandas | ≥ 2.2.0 |
| websockets | ≥ 13.0 |
| python-dotenv | ≥ 1.0.1 |

### Frontend
| Package | Version |
|---|---|
| React | 18 |
| TypeScript | 5 |
| Vite | 5 |
| Zustand | 4 |

---

## Installation

### Option A — Docker (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/AdaptiveUI.git
cd AdaptiveUI

# 2. Start all services (PostgreSQL, backend, frontend)
docker compose up --build

# 3. In a separate terminal, run database migrations
docker compose exec backend alembic upgrade head

# 4. (Optional) Seed clinical cases
docker compose exec backend python seed_cases.py
```

The app will be available at **http://localhost:3000**.  
The API will be available at **http://localhost:8000**.

---

### Option B — Local (without Docker)

#### 1. PostgreSQL

Create a database and user:

```sql
CREATE USER aui WITH PASSWORD 'aui';
CREATE DATABASE adaptiveui OWNER aui;
```

#### 2. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env            # then edit .env (see Environment Variables below)

# Run migrations
alembic upgrade head

# Seed clinical cases
python seed_cases.py

# Start the server
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Create a `.env` file inside the `backend/` directory. All fields are optional except `DATABASE_URL`.

```env
# Required
DATABASE_URL=postgresql+asyncpg://aui:aui@localhost:5432/adaptiveui

# Project Implicit population datasets
# Each CSV must contain a `d_score` column (Harvard Project Implicit format)
# Leave blank to use hardcoded population priors instead
IMPLICIT_BIAS_AGE_DATASET_PATH=../Dataset/Implicit bias/Age IAT.public.2002-2021.csv
IMPLICIT_BIAS_GENDER_DATASET_PATH=../Dataset/Implicit bias/Gender-Career IAT.public.2005-2020.csv
IMPLICIT_BIAS_RACE_DATASET_PATH=../Dataset/Implicit bias/Race IAT.public.2002-2003.csv

# Fatigue seed dataset
# CSV must contain: tortuosity, tau_deviation, stutter_count,
#                   velocity_variance, acceleration_variance, time_on_task,
#                   w_fatigue, s_bias, label
FATIGUE_DATASET_PATH=../Dataset/human_decision_fatigue_dataset.csv

# Bootstrap rules cache (auto-generated on first startup)
BOOTSTRAP_RULES_CACHE_PATH=bootstrap_rules_cache.json

# Population priors used when CSV paths are blank or invalid
S_BIAS_PRIOR_AGE=0.35
S_BIAS_PRIOR_GENDER=0.30
S_BIAS_PRIOR_RACE=0.40
```

> **Note on large CSVs:** The Project Implicit datasets can exceed 1–2 GB. The loader samples up to 50,000 rows using `pandas` with `nrows` — startup takes approximately 8 seconds with all three datasets configured.

---

## Dataset Setup

The `Dataset/` directory should contain:

```
Dataset/
├── Implicit bias/
│   ├── Age IAT.public.2002-2021.csv          # Harvard Project Implicit
│   ├── Gender-Career IAT.public.2005-2020.csv
│   └── Race IAT.public.2002-2003.csv         # (or any year file)
└── human_decision_fatigue_dataset.csv
```

Project Implicit datasets are available at [osf.io/y9hiq](https://osf.io/y9hiq). The fatigue dataset must be provided separately. If either is absent, the system starts in graceful-degradation mode using hardcoded priors and an empty Information System.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

---

## Project Structure

```
AdaptiveUI/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   ├── core/             # Config, database, WebSocket
│   │   ├── engine/           # RST engine, risk model, dataset loader
│   │   ├── middleware/        # Kinematic processor
│   │   ├── models/           # SQLAlchemy DB models + Pydantic schemas
│   │   └── services/         # Business logic (IAT, nudge, profile, case)
│   ├── alembic/              # Database migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/       # React UI components
│       ├── store/            # Zustand global state
│       └── services/         # API + WebSocket clients
├── Dataset/                  # Local datasets (not committed to git)
├── docker-compose.yml
└── README.md
```
