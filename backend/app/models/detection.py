from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import DetectionStatus, ObjectClass


def _uuid() -> str:
    return str(uuid.uuid4())


class Detection(Base):
    """
    A single suspected marine-debris / ghost-gear observation.

    Geometry is stored as a GeoJSON dict (works identically on SQLite and
    PostGIS-backed Postgres). Spatial operations are performed in Python
    via Shapely rather than relying on database-side geometry functions,
    so this schema is portable between SQLite (used for the zero-dependency
    demo) and PostgreSQL/PostGIS (recommended for production).
    """

    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String, unique=True, index=True)

    geometry: Mapped[dict] = mapped_column(JSON)  # GeoJSON Point or Polygon
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    confidence: Mapped[float] = mapped_column(Float)
    object_class: Mapped[str] = mapped_column(String, default=ObjectClass.UNKNOWN_FLOATING_OBJECT.value)
    status: Mapped[str] = mapped_column(String, default=DetectionStatus.UNVERIFIED.value)
    incident_status: Mapped[str] = mapped_column(String, default="unverified")
    assigned_to: Mapped[str] = mapped_column(String, default="")
    assigned_team: Mapped[str] = mapped_column(String, default="")
    verification_notes: Mapped[str] = mapped_column(String, default="")
    verified_by: Mapped[str] = mapped_column(String, default="")
    verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    timestamp: Mapped[dt.datetime] = mapped_column(DateTime)

    source: Mapped[str] = mapped_column(String, default="mock")
    scene_id: Mapped[str] = mapped_column(String, default="")
    area_m2: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": self.geometry,
            "properties": {
                "id": self.id,
                "external_id": self.external_id,
                "confidence": self.confidence,
                "object_class": self.object_class,
                "status": self.status,
                "incident_status": self.incident_status or self.status,
                "assigned_to": self.assigned_to,
                "assigned_team": self.assigned_team,
                "verification_notes": self.verification_notes,
                "verified_by": self.verified_by,
                "verified_at": self.verified_at.isoformat() if self.verified_at else None,
                "is_actionable_alert": self.confidence >= 0.70,
                "timestamp": self.timestamp.isoformat(),
                "source": self.source,
                "scene_id": self.scene_id,
                "area_m2": self.area_m2,
            },
        }
