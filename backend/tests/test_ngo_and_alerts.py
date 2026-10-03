"""Tests for NGO / Responder authentication, incident workflow, and ecological alerts."""
from __future__ import annotations

import pytest

from app.database import SessionLocal, init_db
from app.models.alert import EcologicalAlert
from app.models.detection import Detection
from app.models.user import IncidentAction, User
from app.seed import seed_demo_data


@pytest.fixture(autouse=True)
def setup_test_db(db_session):
    """Ensure database has tables and seeded data."""
    init_db()
    seed_demo_data(db_session)


def test_user_registration_and_login(client):
    email = "new_responder@testmarine.org"
    # Register
    reg_resp = client.post(
        "/api/v1/users/register",
        json={
            "email": email,
            "password": "strongPassword123",
            "full_name": "Test Responder",
            "organization": "Test Marine Watch",
            "role": "responder",
            "phone": "+91-90000-00000",
        },
    )
    assert reg_resp.status_code == 201
    assert reg_resp.json()["email"] == email.lower()

    # Login
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": email, "password": "strongPassword123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token

    # /me
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["full_name"] == "Test Responder"


def test_alerts_inbox_and_incident_lifecycle(client):
    # Login with seeded demo responder
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": "responder@oceanguard.org", "password": "responder123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get responder alerts inbox
    inbox_resp = client.get("/api/v1/users/alerts", headers=headers)
    assert inbox_resp.status_code == 200
    inbox_data = inbox_resp.json()
    assert "verification_queue" in inbox_data
    assert "actionable_alerts" in inbox_data
    assert inbox_data["total_actionable"] >= 1

    # Verify a detection
    action_resp = client.post(
        "/api/v1/users/incidents/DEMO-006/update",
        headers=headers,
        json={"action": "verify", "notes": "Visual sighting confirmed by patrol boat."},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["new_status"] == "verified"

    # Assign detection
    assign_resp = client.post(
        "/api/v1/users/incidents/DEMO-006/update",
        headers=headers,
        json={"action": "assign", "assigned_team": "Team Alpha", "notes": "Dispatched vessel."},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["new_status"] == "assigned"

    # History
    hist_resp = client.get("/api/v1/users/incidents/DEMO-006/history", headers=headers)
    assert hist_resp.status_code == 200
    actions = hist_resp.json()["actions"]
    assert len(actions) >= 2


def test_ecological_alerts_endpoints(client):
    # List alerts
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert data["total"] > 0

    # Active alerts
    active_resp = client.get("/api/v1/alerts/active")
    assert active_resp.status_code == 200
    assert active_resp.json()["total_active"] > 0

    first_alert = active_resp.json()["alerts"][0]
    alert_id = first_alert["id"]

    # Acknowledge alert
    ack_resp = client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    # GeoJSON of alert points
    geo_resp = client.get("/api/v1/alerts/map/geojson")
    assert geo_resp.status_code == 200
    assert geo_resp.json()["type"] == "FeatureCollection"


def test_new_map_layers(client):
    r_coral = client.get("/api/v1/map/coral-reefs")
    assert r_coral.status_code == 200
    assert len(r_coral.json()["features"]) > 0

    r_species = client.get("/api/v1/map/species-habitats")
    assert r_species.status_code == 200
    assert len(r_species.json()["features"]) > 0
