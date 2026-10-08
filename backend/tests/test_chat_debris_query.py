"""Tests for chat debris database query — spatial corridor filter, date resolution, and hotspot clustering."""
from __future__ import annotations

import datetime as dt
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from shapely.geometry import Point

from app.chat.geometry_utils import destination_point, build_corridor
from app.chat.debris_query import query_debris_in_corridor, _object_class_bucket, _build_hotspots
from app.chat.schemas import DebrisSummary


class FakeDetection:
    def __init__(self, id: int, lat: float, lon: float, object_class: str, timestamp: dt.datetime, confidence: float = 0.85):
        self.id = id
        self.latitude = lat
        self.longitude = lon
        self.object_class = object_class
        self.timestamp = timestamp
        self.confidence = confidence


def test_object_class_bucket():
    assert _object_class_bucket("suspected_ghost_gear") == "ghost_net"
    assert _object_class_bucket("marine_debris") == "debris"
    assert _object_class_bucket("plastic_debris") == "debris"
    assert _object_class_bucket("other_cargo") == "unknown"


def test_debris_query_corridor_filter():
    origin_lat, origin_lon = 22.46, 69.87
    dest_lat, dest_lon = destination_point(origin_lat, origin_lon, 270.0, 40.0)
    corridor = build_corridor(origin_lat, origin_lon, dest_lat, dest_lon, radius_km=5.0)

    target_date = dt.date(2026, 10, 9)
    ts = dt.datetime(2026, 10, 9, 10, 0, 0)

    # 1. Point right along route corridor
    mid_lat, mid_lon = (origin_lat + dest_lat) / 2, (origin_lon + dest_lon) / 2
    d1 = FakeDetection(1, mid_lat, mid_lon, "suspected_ghost_gear", ts)

    # 2. Point near start of corridor
    d2 = FakeDetection(2, origin_lat, origin_lon, "marine_debris", ts)

    # 3. Point far away (e.g. 100km north, completely outside)
    d3 = FakeDetection(3, 23.5, 69.87, "suspected_ghost_gear", ts)

    # 4. Point along route but different date (2026-10-15)
    d4 = FakeDetection(4, mid_lat, mid_lon, "marine_debris", dt.datetime(2026, 10, 15, 10, 0, 0))

    mock_db = MagicMock()
    # Filter returns all 4 as candidates from bounding box
    mock_db.query.return_value.filter.return_value.all.return_value = [d1, d2, d3, d4]

    summary = query_debris_in_corridor(
        db=mock_db,
        corridor_polygon=corridor,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        date_iso="2026-10-09",
    )

    # Only d1 and d2 are inside corridor on 2026-10-09
    assert summary.total_debris == 2
    assert summary.ghost_nets == 1
    assert summary.other_debris == 1
    assert summary.data_date == "2026-10-09"
    assert len(summary.hotspots) >= 1


def test_debris_query_nearest_date_fallback():
    origin_lat, origin_lon = 22.46, 69.87
    dest_lat, dest_lon = destination_point(origin_lat, origin_lon, 270.0, 40.0)
    corridor = build_corridor(origin_lat, origin_lon, dest_lat, dest_lon, radius_km=5.0)

    # Target date is 2026-10-09, but detection is on 2026-10-10 (1 day diff <= 7 days tolerance)
    ts_nearby = dt.datetime(2026, 10, 10, 8, 0, 0)
    mid_lat, mid_lon = (origin_lat + dest_lat) / 2, (origin_lon + dest_lon) / 2
    d1 = FakeDetection(1, mid_lat, mid_lon, "suspected_ghost_gear", ts_nearby)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [d1]

    summary = query_debris_in_corridor(
        db=mock_db,
        corridor_polygon=corridor,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        date_iso="2026-10-09",
        date_tolerance_days=7,
    )

    assert summary.total_debris == 1
    assert summary.ghost_nets == 1
    assert summary.nearest_available_date == "2026-10-10"


def test_hotspot_clustering():
    origin_lat, origin_lon = 22.0, 70.0
    ts = dt.datetime.now()

    # Create 3 points in one cluster near (22.2, 70.2)
    c1 = [
        FakeDetection(1, 22.201, 70.201, "suspected_ghost_gear", ts, 0.9),
        FakeDetection(2, 22.202, 70.202, "suspected_ghost_gear", ts, 0.8),
        FakeDetection(3, 22.199, 70.198, "marine_debris", ts, 0.85),
    ]
    # Create 1 point far away near (22.8, 70.8)
    c2 = [
        FakeDetection(4, 22.80, 70.80, "marine_debris", ts, 0.75),
    ]

    hotspots = _build_hotspots(c1 + c2, origin_lat, origin_lon, grid_size_deg=0.2, max_clusters=5)
    assert len(hotspots) == 2
    # The first cluster (3 detections) should have count 3
    counts = [h.count for h in hotspots]
    assert 3 in counts
    assert 1 in counts
