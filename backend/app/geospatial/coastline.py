from __future__ import annotations

from shapely.geometry import Point

from app.geospatial.loaders import features_with_geometry, load_coastline

_DEGREE_TO_KM = 111.32


def distance_to_coastline_km(lat: float, lon: float) -> float:
    """
    Great-circle-approximate distance (km) from a point to the nearest
    demo coastline segment, using simple degree->km scaling (adequate for
    the demo dataset's coarse resolution; a production system would use a
    proper geodesic distance via pyproj.Geod).
    """
    point = Point(lon, lat)
    min_deg = min(geom.distance(point) for _, geom in features_with_geometry(load_coastline()))
    return round(min_deg * _DEGREE_TO_KM, 2)
