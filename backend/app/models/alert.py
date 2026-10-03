from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class EcologicalAlert(Base):
    """
    Real-time ecological and marine-life alert triggered when marine debris or its
    predicted drift intersects or approaches protected areas, coral reefs,
    turtle nesting grounds, or cetacean corridors.
    """

    __tablename__ = "ecological_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    detection_id: Mapped[str] = mapped_column(String, ForeignKey("detections.id"), index=True)
    external_id: Mapped[str] = mapped_column(String, index=True)

    alert_type: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status: Mapped[str] = mapped_column(String, default="active", index=True)  # active, acknowledged, in_progress, resolved

    headline: Mapped[str] = mapped_column(String)
    details: Mapped[str] = mapped_column(Text)
    region_name: Mapped[str] = mapped_column(String)
    feature_type: Mapped[str] = mapped_column(String)  # protected_area, coral_reef, turtle_nesting, mammal_corridor, mangrove

    species_at_risk: Mapped[list] = mapped_column(JSON, default=list)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_impact_hours: Mapped[float] = mapped_column(Float, default=0.0)
    impact_point_geometry: Mapped[dict] = mapped_column(JSON, default=dict)

    recommended_action: Mapped[str] = mapped_column(Text, default="")
    source_citation: Mapped[str] = mapped_column(String, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "detection_id": self.detection_id,
            "external_id": self.external_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "status": self.status,
            "headline": self.headline,
            "details": self.details,
            "region_name": self.region_name,
            "feature_type": self.feature_type,
            "species_at_risk": self.species_at_risk,
            "distance_km": self.distance_km,
            "estimated_impact_hours": self.estimated_impact_hours,
            "impact_point_geometry": self.impact_point_geometry,
            "recommended_action": self.recommended_action,
            "source_citation": self.source_citation,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
