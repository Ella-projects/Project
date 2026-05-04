from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, cases, iat, nudge, profile, session, telemetry
from app.engine.dataset_loader import initialise_from_datasets
from app.engine.information_system import is_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialise_from_datasets(is_registry)
    yield


app = FastAPI(
    title="Adaptive User Interface — API",
    description="Closed-loop kinematic telemetry and cognitive bias mitigation system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(session.router)
app.include_router(profile.router)
app.include_router(iat.router)
app.include_router(nudge.router)
app.include_router(cases.router)
app.include_router(analysis.router)

# WebSocket route
app.include_router(telemetry.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
