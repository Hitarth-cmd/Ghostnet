from __future__ import annotations

import datetime as dt
import random

from app.detection.providers.base import DetectionProvider, DetectionRecord
from app.models.enums import DetectionStatus, ObjectClass

# Fixed seed -> the demo dataset is identical every time the app starts.
# This is intentional: reviewers/graders must see the same detections on
# every run, not a different random scatter each refresh.
_SEED = 20260908

# Anchor points around real Indian coastal regions. These are approximate
# coastal reference coordinates used only to place plausible DEMO markers -
# they are not derived from any actual satellite observation.
_ANCHORS = [
    ("Goa coast", 15.32, 72.71),
    ("Mumbai coast", 18.94, 72.62),
    ("Kochi coast", 9.93, 76.20),
    ("Chennai coast", 13.05, 80.10),
    ("Visakhapatnam coast", 17.68, 83.25),
    ("Gulf of Mannar", 9.15, 79.15),
    ("Sundarbans coast", 21.60, 88.90),
    ("Lakshadweep vicinity", 10.57, 72.64),
    ("Gujarat coast (Kutch)", 22.45, 69.05),
    ("Andaman vicinity", 11.62, 92.72),
]

_CLASSES = [
    ObjectClass.SUSPECTED_GHOST_GEAR,
    ObjectClass.MARINE_DEBRIS,
    ObjectClass.UNKNOWN_FLOATING_OBJECT,
]

_STATUSES = [
    DetectionStatus.UNVERIFIED,
    DetectionStatus.UNVERIFIED,
    DetectionStatus.UNVERIFIED,
    DetectionStatus.VERIFIED,
    DetectionStatus.RECOVERED,
]


def _build_demo_records() -> list[DetectionRecord]:
    rng = random.Random(_SEED)
    base_time = dt.datetime(2026, 9, 8, 6, 0, 0)
    records: list[DetectionRecord] = []

    for i, (region, lat0, lon0) in enumerate(_ANCHORS, start=1):
        external_id = f"DEMO-{i:03d}"
        # Small deterministic jitter so points don't sit exactly on the
        # anchor, but the jitter is seeded so it never changes between runs.
        jitter_lat = rng.uniform(-0.35, 0.35)
        jitter_lon = rng.uniform(-0.35, 0.35)
        lat = round(lat0 + jitter_lat, 5)
        lon = round(lon0 + jitter_lon, 5)

        confidence = round(rng.uniform(0.55, 0.97), 3)
        object_class = _CLASSES[rng.randrange(len(_CLASSES))]
        status = _STATUSES[rng.randrange(len(_STATUSES))]
        timestamp = base_time + dt.timedelta(hours=rng.randint(0, 96))
        area_m2 = round(rng.uniform(8.0, 620.0), 1)

        records.append(
            DetectionRecord(
                external_id=external_id,
                latitude=lat,
                longitude=lon,
                confidence=confidence,
                object_class=object_class,
                status=status,
                timestamp=timestamp,
                source="mock-demo",
                scene_id=f"DEMO-SCENE-{region.split()[0].upper()}-{i:03d}",
                area_m2=area_m2,
            )
        )
    return records


class MockDetectionProvider(DetectionProvider):
    """
    Deterministic DEMO/MOCK detection provider.

    This is what makes the entire downstream platform (drift, geospatial,
    risk, RAG, reporting, dashboard) demonstrable without the real
    Sentinel-2 segmentation model. All detections are clearly sourced as
    "mock-demo" and must be shown as DEMO/UNVERIFIED in the UI unless a
    human has changed their status.
    """

    name = "mock"

    def __init__(self) -> None:
        self._records = {r.external_id: r for r in _build_demo_records()}

    def detect(self, **kwargs) -> list[DetectionRecord]:
        # A "detect" call against the mock provider simply returns the
        # deterministic demo catalogue - there is no live inference.
        return list(self._records.values())

    def get_detection(self, external_id: str) -> DetectionRecord | None:
        return self._records.get(external_id)

    def list_detections(self) -> list[DetectionRecord]:
        return list(self._records.values())
