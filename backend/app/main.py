from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "src"))

from app.api.routes import router
from app.core.config import settings
from app.services.inference import InferenceService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.inference = InferenceService(settings.model_path)
    yield


app = FastAPI(title="AquaX API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Mount router at /api/v1 (primary) and bare / for /health convenience
app.include_router(router, prefix="/api/v1")
app.include_router(router)  # bare prefix for /health, /detect fallback
