from __future__ import annotations

import time


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_list_detections_returns_demo_data(client):
    r = client.get("/api/v1/detections")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 10
    assert any(item["external_id"] == "DEMO-001" for item in body["items"])


def test_get_single_detection(client):
    r = client.get("/api/v1/detections/DEMO-002")
    assert r.status_code == 200
    assert r.json()["external_id"] == "DEMO-002"


def test_get_missing_detection_404s(client):
    r = client.get("/api/v1/detections/NOT-REAL")
    assert r.status_code == 404


def test_create_detection(client):
    payload = {
        "external_id": "MANUAL-TEST-001",
        "latitude": 12.0,
        "longitude": 80.0,
        "confidence": 0.75,
        "object_class": "marine_debris",
        "status": "unverified",
        "source": "manual-test",
    }
    r = client.post("/api/v1/detections", json=payload)
    assert r.status_code == 201
    assert r.json()["external_id"] == "MANUAL-TEST-001"

    # Duplicate external_id should conflict.
    r2 = client.post("/api/v1/detections", json=payload)
    assert r2.status_code == 409


def test_analyze_sync_returns_complete_result(client):
    r = client.post("/api/v1/detections/DEMO-004/analyze", params={"sync": True})
    assert r.status_code == 200
    body = r.json()
    assert body["detection_id"] == "DEMO-004"
    assert "risk" in body and "priority" in body and "report" in body


def test_drift_risk_report_endpoints_after_analysis(client):
    client.post("/api/v1/detections/DEMO-005/analyze", params={"sync": True})

    r_drift = client.get("/api/v1/detections/DEMO-005/drift")
    assert r_drift.status_code == 200
    assert len(r_drift.json()["horizons"]) == 3

    r_risk = client.get("/api/v1/detections/DEMO-005/risk")
    assert r_risk.status_code == 200
    assert "risk_score" in r_risk.json()

    r_report = client.get("/api/v1/detections/DEMO-005/report")
    assert r_report.status_code == 200
    assert "summary" in r_report.json()


def test_analyze_async_job_completes(client):
    r = client.post("/api/v1/detections/DEMO-007/analyze")
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "queued"

    for _ in range(50):
        rj = client.get(f"/api/v1/jobs/{job_id}")
        assert rj.status_code == 200
        if rj.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert rj.json()["status"] == "completed"
    assert rj.json()["result"]["detection_id"] == "DEMO-007"


def test_job_not_found_404s(client):
    r = client.get("/api/v1/jobs/does-not-exist")
    assert r.status_code == 404


def test_system_status_endpoint(client):
    r = client.get("/api/v1/system/status")
    assert r.status_code == 200
    body = r.json()
    assert body["model_provider"] == "mock"
    assert body["data_mode"] == "demo"
