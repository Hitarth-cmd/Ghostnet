from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import detections, inference, jobs, map as map_api, system
from app.api import users, alerts
from app.api import chat as chat_api
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.seed import seed_demo_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ghostnet.main")

settings = get_settings()

app = FastAPI(
    title="OceanGuard — Marine Debris Intelligence Platform",
    description=(
        "End-to-end AI-powered marine debris detection, drift forecasting, "
        "ecological risk assessment, NGO/responder coordination, and evidence-based reporting. "
        "DEMO mode requires no external services, API keys, or ML model."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()

    # Pre-load and cache ecological data layers (coral reefs, species habitats, extended MPAs)
    try:
        from app.geospatial.data_collector import preload_all
        preload_all()
    except Exception as exc:
        logger.warning("[STARTUP] Ecological data preload failed (non-fatal): %s", exc)

    logger.info(
        "[STARTUP] OceanGuard ready (DATA_MODE=%s, MODEL_PROVIDER=%s)",
        settings.DATA_MODE,
        settings.MODEL_PROVIDER,
    )


app.include_router(system.router)
app.include_router(detections.router)
app.include_router(map_api.router)
app.include_router(jobs.router)
app.include_router(inference.router)
app.include_router(users.router)
app.include_router(alerts.router)
app.include_router(chat_api.router)
