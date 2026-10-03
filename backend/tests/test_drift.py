from __future__ import annotations

import datetime as dt

from app.drift.schemas import DriftRequest
from app.drift.trajectory import forecast_drift
from app.drift.visualization import drift_result_to_geojson


def test_drift_forecast_produces_all_horizons():
    request = DriftRequest(
        detection_id="TEST-001",
        latitude=15.32,
        longitude=72.71,
        start_time=dt.datetime(2026, 9, 8, 6, 0, 0),
    )
    result = forecast_drift(request)
    assert result.mode == "demo"
    hours = sorted(h.forecast_hour for h in result.horizons)
    assert hours == [24, 48, 72]


def test_drift_is_deterministic():
    request = DriftRequest(
        detection_id="TEST-002",
        latitude=9.93,
        longitude=76.20,
        start_time=dt.datetime(2026, 9, 8, 6, 0, 0),
    )
    r1 = forecast_drift(request)
    r2 = forecast_drift(request)
    for h1, h2 in zip(r1.horizons, r2.horizons):
        assert h1.mean_latitude == h2.mean_latitude
        assert h1.mean_longitude == h2.mean_longitude


def test_drift_positions_move_over_time():
    request = DriftRequest(
        detection_id="TEST-003",
        latitude=13.05,
        longitude=80.10,
        start_time=dt.datetime(2026, 9, 8, 6, 0, 0),
    )
    result = forecast_drift(request)
    # The 72h position should differ from the 24h position (particles moved).
    h24 = next(h for h in result.horizons if h.forecast_hour == 24)
    h72 = next(h for h in result.horizons if h.forecast_hour == 72)
    assert (h24.mean_latitude, h24.mean_longitude) != (h72.mean_latitude, h72.mean_longitude)


def test_uncertainty_geometry_is_valid_polygon():
    request = DriftRequest(
        detection_id="TEST-004",
        latitude=18.94,
        longitude=72.62,
        start_time=dt.datetime(2026, 9, 8, 6, 0, 0),
    )
    result = forecast_drift(request)
    for h in result.horizons:
        assert h.uncertainty_geometry["type"] == "Polygon"
        assert len(h.uncertainty_geometry["coordinates"][0]) >= 4


def test_drift_result_to_geojson_has_required_properties():
    request = DriftRequest(
        detection_id="TEST-005",
        latitude=17.68,
        longitude=83.25,
        start_time=dt.datetime(2026, 9, 8, 6, 0, 0),
    )
    result = forecast_drift(request)
    geojson = drift_result_to_geojson(result, origin_lat=17.68, origin_lon=83.25)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
    for feature in geojson["features"]:
        props = feature["properties"]
        for key in ("detection_id", "forecast_hour", "timestamp", "source", "mode"):
            assert key in props
