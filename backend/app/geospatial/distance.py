from __future__ import annotations

from shapely.geometry import Point, shape

from app.geospatial.loaders import features_with_geometry, load_protected_areas

_DEGREE_TO_KM = 111.32


def distance_to_nearest_protected_area_km(lat: float, lon: float) -> tuple[float, str | None]:
    point = Point(lon, lat)
    best_km, best_name = None, None
    for feature, geom in features_with_geometry(load_protected_areas()):
        d_km = geom.distance(point) * _DEGREE_TO_KM
        if best_km is None or d_km < best_km:
            best_km, best_name = d_km, feature["properties"]["name"]
    return round(best_km or 0.0, 2), best_name


def time_to_protected_area_hours(distance_km: float, drift_speed_kmh: float = 0.5) -> float:
    """
    Rough decision-support estimate of how many hours of drift at a
    representative synthetic drift speed it would take to reach the
    nearest protected area. NOT a guaranteed arrival time.
    """
    if drift_speed_kmh <= 0:
        return float("inf")
    return round(distance_km / drift_speed_kmh, 1)
