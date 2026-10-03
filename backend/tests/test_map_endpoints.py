from __future__ import annotations


def test_map_detections_is_valid_geojson(client):
    r = client.get("/api/v1/map/detections")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) >= 10
    for feature in body["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        assert "external_id" in feature["properties"]


def test_map_trajectories_after_analysis_is_valid_geojson(client):
    client.post("/api/v1/detections/DEMO-008/analyze", params={"sync": True})
    r = client.get("/api/v1/map/trajectories")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) > 0
    layers = {f["properties"]["layer"] for f in body["features"]}
    assert "uncertainty_polygon" in layers


def test_map_protected_areas_is_labeled_demo(client):
    r = client.get("/api/v1/map/protected-areas")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert "DEMO" in body["properties"]["note"] or "demo" in body["properties"]["license"].lower()


def test_map_habitats_is_valid_geojson(client):
    r = client.get("/api/v1/map/habitats")
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"


def test_map_layers_lists_all_layers(client):
    r = client.get("/api/v1/map/layers")
    assert r.status_code == 200
    ids = {layer["id"] for layer in r.json()["layers"]}
    assert {"detections", "trajectories", "risk_zones", "protected_areas", "habitats"}.issubset(ids)


def test_map_risk_zones_only_shows_high_or_critical(client):
    r = client.get("/api/v1/map/risk-zones")
    assert r.status_code == 200
    body = r.json()
    for feature in body["features"]:
        assert feature["properties"]["risk_level"] in ("HIGH", "CRITICAL")
