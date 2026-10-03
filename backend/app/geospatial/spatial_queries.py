from __future__ import annotations

from shapely.geometry import Point, shape

from app.geospatial.coastline import distance_to_coastline_km
from app.geospatial.distance import distance_to_nearest_protected_area_km, time_to_protected_area_hours
from app.geospatial.habitat import habitat_overlaps
from app.geospatial.protected_area import protected_area_overlaps


def analyze_geometry(geometry: dict, lat: float, lon: float) -> dict:
    """
    One-stop spatial analysis for a detection/forecast geometry: which
    demo MPAs and habitats it overlaps, and distance to coastline / nearest
    protected area. Used by both the risk engine and the report generator.
    """
    geom = shape(geometry)
    mpa_hits = protected_area_overlaps(geom)
    habitat_hits = habitat_overlaps(geom)
    coastline_km = distance_to_coastline_km(lat, lon)
    mpa_distance_km, nearest_mpa_name = distance_to_nearest_protected_area_km(lat, lon)

    return {
        "protected_area_overlap": len(mpa_hits) > 0,
        "protected_areas": [f["properties"]["name"] for f in mpa_hits],
        "habitat_overlap": len(habitat_hits) > 0,
        "habitats": [f["properties"]["name"] for f in habitat_hits],
        "habitat_kinds": sorted({f["properties"].get("habitat_kind", "unknown") for f in habitat_hits}),
        "distance_to_coastline_km": coastline_km,
        "distance_to_nearest_protected_area_km": mpa_distance_km,
        "nearest_protected_area": nearest_mpa_name,
        "estimated_time_to_protected_area_hours": time_to_protected_area_hours(mpa_distance_km),
    }


def point_in_any_polygon(lat: float, lon: float, feature_collection: dict) -> bool:
    point = Point(lon, lat)
    return any(shape(f["geometry"]).contains(point) for f in feature_collection["features"])
