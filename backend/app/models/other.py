from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Trajectory(Base):
    """One forecast horizon (24h/48h/72h) of drift for a detection."""

    __tablename__ = "trajectories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    detection_id: Mapped[str] = mapped_column(String, ForeignKey("detections.id"), index=True)
    forecast_hour: Mapped[int] = mapped_column(Integer)  # 24 / 48 / 72
    mode: Mapped[str] = mapped_column(String)  # demo / live
    source: Mapped[str] = mapped_column(String, default="ghostnet-drift-engine")

    position_geometry: Mapped[dict] = mapped_column(JSON)  # ensemble-mean point
    uncertainty_geometry: Mapped[dict] = mapped_column(JSON)  # polygon
    particle_geometry: Mapped[dict] = mapped_column(JSON)  # multipoint of all particles

    timestamp: Mapped[dt.datetime] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    detection_id: Mapped[str] = mapped_column(String, ForeignKey("detections.id"), index=True)

    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String)
    feature_values: Mapped[dict] = mapped_column(JSON)
    feature_contributions: Mapped[dict] = mapped_column(JSON)
    reason_codes: Mapped[list] = mapped_column(JSON)

    priority_rank: Mapped[int] = mapped_column(Integer, default=0)
    priority_level: Mapped[str] = mapped_column(String, default="LOW")
    recommended_action: Mapped[str] = mapped_column(String, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class SpatialFeature(Base):
    """A demo or authoritative geospatial layer feature (MPA/habitat/coastline)."""

    __tablename__ = "spatial_features"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    feature_type: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    geometry: Mapped[dict] = mapped_column(JSON)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)

    source_name: Mapped[str] = mapped_column(String, default="GhostNet Demo Dataset")
    source_url: Mapped[str] = mapped_column(String, default="")
    retrieved_at: Mapped[str] = mapped_column(String, default="")
    license: Mapped[str] = mapped_column(String, default="Demo / synthetic - not for operational use")
    dataset_version: Mapped[str] = mapped_column(String, default="demo-1.0")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    detection_id: Mapped[str] = mapped_column(String, ForeignKey("detections.id"), index=True)
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(String, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )


class DataSource(Base):
    """Provenance record for any dataset loaded into the platform."""

    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(String, default="")
    license: Mapped[str] = mapped_column(String, default="")
    retrieved_at: Mapped[str] = mapped_column(String, default="")
    dataset_version: Mapped[str] = mapped_column(String, default="")
    is_demo: Mapped[bool] = mapped_column(default=True)
