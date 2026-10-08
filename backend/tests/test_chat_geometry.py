"""Tests for chat geometry utilities — geodesic destination and corridor building."""
from __future__ import annotations

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.chat.geometry_utils import (
    destination_point,
    build_corridor,
    distance_along_route_km,
    cardinal_to_bearing,
    bearing_label,
)


# ── Cardinal bearing conversion ───────────────────────────────────────────────

def test_cardinal_west():
    assert cardinal_to_bearing("west") == pytest.approx(270.0)

def test_cardinal_north():
    assert cardinal_to_bearing("north") == pytest.approx(0.0)

def test_cardinal_sw():
    assert cardinal_to_bearing("sw") == pytest.approx(225.0)

def test_cardinal_unknown():
    assert cardinal_to_bearing("foobar") is None

def test_bearing_label_west():
    assert bearing_label(270.0) == "west"

def test_bearing_label_northeast():
    assert bearing_label(45.0) == "northeast"


# ── Destination point accuracy ────────────────────────────────────────────────

def test_destination_due_east():
    """Moving due east (90°) from origin should increase longitude, keep lat same."""
    lat0, lon0 = 22.0, 70.0
    lat1, lon1 = destination_point(lat0, lon0, 90.0, 100.0)
    assert abs(lat1 - lat0) < 0.05          # lat should barely change
    assert lon1 > lon0                      # lon increases eastward


def test_destination_due_north():
    lat0, lon0 = 22.0, 70.0
    lat1, lon1 = destination_point(lat0, lon0, 0.0, 100.0)
    assert lat1 > lat0                      # lat increases northward
    assert abs(lon1 - lon0) < 0.05         # lon barely changes


def test_destination_distance_accuracy():
    """100 km due east: destination should be ~100 km from origin."""
    lat0, lon0 = 22.0, 70.0
    lat1, lon1 = destination_point(lat0, lon0, 90.0, 100.0)
    dist = distance_along_route_km(lat0, lon0, lat1, lon1)
    assert dist == pytest.approx(100.0, rel=0.005)  # within 0.5%


def test_destination_40km_west():
    """Gulf of Kutch → 40 km west should end up in Arabian Sea."""
    lat0, lon0 = 22.46, 69.87  # Gulf of Kutch
    lat1, lon1 = destination_point(lat0, lon0, 270.0, 40.0)
    assert lon1 < lon0   # moved west
    dist = distance_along_route_km(lat0, lon0, lat1, lon1)
    assert dist == pytest.approx(40.0, rel=0.01)


# ── Corridor polygon ──────────────────────────────────────────────────────────

def test_corridor_is_polygon():
    from shapely.geometry.polygon import Polygon
    lat0, lon0 = 22.46, 69.87
    lat1, lon1 = destination_point(lat0, lon0, 270.0, 40.0)
    corridor = build_corridor(lat0, lon0, lat1, lon1, radius_km=5.0)
    assert isinstance(corridor, Polygon)
    assert corridor.is_valid
    assert not corridor.is_empty


def test_corridor_contains_route_midpoint():
    """The midpoint of the route must lie inside the corridor."""
    lat0, lon0 = 22.46, 69.87
    lat1, lon1 = destination_point(lat0, lon0, 270.0, 40.0)
    corridor = build_corridor(lat0, lon0, lat1, lon1, radius_km=5.0)

    mid_lat = (lat0 + lat1) / 2
    mid_lon = (lon0 + lon1) / 2
    from shapely.geometry import Point
    assert corridor.contains(Point(mid_lon, mid_lat))


def test_larger_radius_encloses_smaller():
    """A 10 km radius corridor should contain a 5 km radius corridor."""
    lat0, lon0 = 22.46, 69.87
    lat1, lon1 = destination_point(lat0, lon0, 270.0, 40.0)
    small = build_corridor(lat0, lon0, lat1, lon1, radius_km=5.0)
    large = build_corridor(lat0, lon0, lat1, lon1, radius_km=10.0)
    assert large.area > small.area


def test_corridor_does_not_contain_far_point():
    """A point 20 km perpendicular to the route should not be in a 5 km buffer."""
    lat0, lon0 = 22.46, 69.87
    lat1, lon1 = destination_point(lat0, lon0, 270.0, 40.0)
    corridor = build_corridor(lat0, lon0, lat1, lon1, radius_km=5.0)
    # Go 20 km north of origin
    far_lat, far_lon = destination_point(lat0, lon0, 0.0, 20.0)
    from shapely.geometry import Point
    assert not corridor.contains(Point(far_lon, far_lat))


# ── Distance helper ───────────────────────────────────────────────────────────

def test_distance_zero():
    assert distance_along_route_km(22.0, 70.0, 22.0, 70.0) == pytest.approx(0.0, abs=0.01)

def test_distance_known():
    # Mundra to Kandla is approx 56 km geodesic distance
    d = distance_along_route_km(22.84, 69.71, 23.03, 70.22)
    assert 40 < d < 70
