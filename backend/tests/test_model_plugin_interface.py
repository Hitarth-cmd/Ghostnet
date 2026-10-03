"""
Proves that replacing the detection provider does not require changing
drift/risk/RAG/frontend: a fake provider (standing in for a real trained
segmentation model) is fed straight through the same orchestrator
pipeline used for the mock provider, with zero special-casing.
"""
from __future__ import annotations

import datetime as dt

from app.detection.providers.base import DetectionProvider, DetectionRecord
from app.models.detection import Detection
from app.models.enums import DetectionStatus, ObjectClass
from app.orchestrator.pipeline import analyze_detection


class FakeSegmentationDetectionProvider(DetectionProvider):
    """
    NOT the real model - a deterministic stand-in that returns a single
    segmentation-derived detection, used only to test the
    model -> detection -> downstream-system interface boundary.
    """

    name = "fake-segmentation-test"

    def __init__(self) -> None:
        self._record = DetectionRecord(
            external_id="PLUGIN-TEST-001",
            latitude=11.0,
            longitude=76.0,
            confidence=0.88,
            object_class=ObjectClass.SUSPECTED_GHOST_GEAR,
            status=DetectionStatus.UNVERIFIED,
            timestamp=dt.datetime(2026, 9, 8, 12, 0, 0),
            source="fake-segmentation-test",
            scene_id="PLUGIN-TEST-SCENE",
        )

    def detect(self, **kwargs):
        return [self._record]

    def get_detection(self, external_id):
        return self._record if external_id == self._record.external_id else None

    def list_detections(self):
        return [self._record]


def test_plugin_provider_flows_through_full_pipeline_unmodified(db_session):
    provider = FakeSegmentationDetectionProvider()
    record = provider.list_detections()[0]

    existing = db_session.query(Detection).filter(Detection.external_id == record.external_id).one_or_none()
    if existing is None:
        db_session.add(
            Detection(
                external_id=record.external_id,
                latitude=record.latitude,
                longitude=record.longitude,
                geometry=record.geometry,
                confidence=record.confidence,
                object_class=record.object_class.value,
                status=record.status.value,
                timestamp=record.timestamp,
                source=record.source,
                scene_id=record.scene_id,
                area_m2=record.area_m2,
            )
        )
        db_session.commit()

    # This is the exact same analyze_detection() call used for mock-provider
    # detections - no drift/risk/RAG/report code path differs by provider.
    result = analyze_detection(db_session, record.external_id)

    assert result.detection_id == "PLUGIN-TEST-001"
    assert result.drift.mode == "demo"
    assert result.risk["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert result.report.detection_id == "PLUGIN-TEST-001"
