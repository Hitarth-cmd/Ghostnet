from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.enums import DetectionStatus, ObjectClass


@dataclass
class DetectionRecord:
    """
    Provider-agnostic detection payload.

    Every DetectionProvider implementation (mock, real Sentinel-2 model,
    or any future provider) must produce a list of these. Nothing
    downstream (drift, risk, RAG, database, API, frontend) knows or
    cares which provider produced them - this dataclass is the entire
    contract.
    """

    external_id: str
    latitude: float
    longitude: float
    confidence: float
    object_class: ObjectClass
    timestamp: dt.datetime
    source: str
    scene_id: str
    geometry: dict = field(default_factory=dict)
    status: DetectionStatus = DetectionStatus.UNVERIFIED
    area_m2: float = 0.0

    def __post_init__(self) -> None:
        if not self.geometry:
            self.geometry = {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            }


class DetectionProvider(ABC):
    """Interface every detection source (mock or real model) must implement."""

    name: str = "base"

    @abstractmethod
    def detect(self, **kwargs) -> list[DetectionRecord]:
        """Run detection and return newly produced DetectionRecord objects."""

    @abstractmethod
    def get_detection(self, external_id: str) -> DetectionRecord | None:
        """Return a single detection by its external id, or None."""

    @abstractmethod
    def list_detections(self) -> list[DetectionRecord]:
        """Return all detections this provider currently knows about."""
