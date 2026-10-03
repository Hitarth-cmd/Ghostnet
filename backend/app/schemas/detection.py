from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DetectionStatus, ObjectClass


class DetectionCreate(BaseModel):
    external_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    confidence: float = Field(ge=0, le=1)
    object_class: ObjectClass = ObjectClass.UNKNOWN_FLOATING_OBJECT
    status: DetectionStatus = DetectionStatus.UNVERIFIED
    timestamp: dt.datetime | None = None
    source: str = "manual"
    scene_id: str = ""
    area_m2: float = 0.0


class DetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    latitude: float
    longitude: float
    confidence: float
    object_class: str
    status: str
    timestamp: dt.datetime
    source: str
    scene_id: str
    area_m2: float
    created_at: dt.datetime
    updated_at: dt.datetime


class DetectionListOut(BaseModel):
    total: int
    items: list[DetectionOut]
