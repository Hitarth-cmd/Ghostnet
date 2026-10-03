from __future__ import annotations

from app.geospatial.intersection import intersection_area_ratio, polygons_intersect
from app.geospatial.spatial_queries import analyze_geometry


def test_point_inside_demo_mpa_detected():
    geom = {"type": "Point", "coordinates": [79.1, 9.15]}
    result = analyze_geometry(geom, 9.15, 79.1)
    assert result["protected_area_overlap"] is True
    assert "DEMO Gulf of Mannar Marine National Park (approx.)" in result["protected_areas"]


def test_point_outside_any_demo_mpa():
    geom = {"type": "Point", "coordinates": [65.0, 5.0]}  # open ocean, far from any demo layer
    result = analyze_geometry(geom, 5.0, 65.0)
    assert result["protected_area_overlap"] is False
    assert result["habitat_overlap"] is False


def test_habitat_overlap_reports_habitat_kind():
    geom = {"type": "Point", "coordinates": [72.6, 10.6]}  # inside DEMO Lakshadweep coral reef zone
    result = analyze_geometry(geom, 10.6, 72.6)
    assert result["habitat_overlap"] is True
    assert "coral_reef" in result["habitat_kinds"]


def test_intersection_area_ratio_full_overlap():
    poly = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    assert intersection_area_ratio(poly, poly) == 1.0


def test_intersection_area_ratio_no_overlap():
    poly_a = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    poly_b = {"type": "Polygon", "coordinates": [[[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]]}
    assert intersection_area_ratio(poly_a, poly_b) == 0.0


def test_polygons_intersect_partial_overlap():
    poly_a = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
    poly_b = {"type": "Polygon", "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]]}
    assert polygons_intersect(poly_a, poly_b) is True


def test_distance_to_coastline_is_nonnegative():
    geom = {"type": "Point", "coordinates": [72.71, 15.32]}
    result = analyze_geometry(geom, 15.32, 72.71)
    assert result["distance_to_coastline_km"] >= 0
