from __future__ import annotations

from app.detection.providers.mock import MockDetectionProvider
from app.models.detection import Detection
from app.seed import seed_demo_data


def test_mock_provider_deterministic():
    p1 = MockDetectionProvider()
    p2 = MockDetectionProvider()
    r1 = {r.external_id: (r.latitude, r.longitude, r.confidence) for r in p1.list_detections()}
    r2 = {r.external_id: (r.latitude, r.longitude, r.confidence) for r in p2.list_detections()}
    assert r1 == r2
    assert len(r1) == 10
    assert "DEMO-001" in r1


def test_mock_provider_get_detection():
    p = MockDetectionProvider()
    record = p.get_detection("DEMO-001")
    assert record is not None
    assert record.external_id == "DEMO-001"
    assert record.geometry["type"] == "Point"


def test_seed_demo_data_is_idempotent(db_session):
    # The test database is shared across the session (see conftest.py), so
    # another test may have already seeded it - this only asserts that
    # calling seed twice never creates duplicates, not that this is the
    # very first seed call.
    seed_demo_data(db_session)
    count_after_first = db_session.query(Detection).count()
    created_second = seed_demo_data(db_session)
    assert created_second == 0
    assert db_session.query(Detection).count() == count_after_first
    # The 10 deterministic demo detections must always be present.
    demo_ids = {d.external_id for d in db_session.query(Detection).all()}
    assert {f"DEMO-{i:03d}" for i in range(1, 11)}.issubset(demo_ids)


def test_detection_to_geojson_feature(db_session):
    detection = db_session.query(Detection).filter(Detection.external_id == "DEMO-001").one()
    feature = detection.to_geojson_feature()
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Point"
    assert feature["properties"]["external_id"] == "DEMO-001"
