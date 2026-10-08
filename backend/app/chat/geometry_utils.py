"""Geodesic geometry utilities for the vessel chat pipeline.

All calculations use the WGS-84 ellipsoid via pyproj.Geod so distances
and bearings are accurate over ocean areas without flat-earth approximation.

Public API:
  destination_point(lat, lon, bearing_deg, distance_km)  → (lat, lon)
  build_corridor(origin_lat, origin_lon, dest_lat, dest_lon, radius_km)
      → Shapely Polygon (the buffered route)
  corridor_to_geojson_feature(polygon, meta)  → GeoJSON Feature dict
  route_to_geojson_feature(origin, destination, meta)  → GeoJSON Feature dict
"""
from __future__ import annotations

import math
from typing import Any

from pyproj import Geod
from shapely.geometry import LineString, Point, mapping

_geod = Geod(ellps="WGS84")

# ─── Bearing helpers ────────────────────────────────────────────────────────

_CARDINAL_BEARINGS: dict[str, float] = {
    "north": 0.0, "n": 0.0,
    "northeast": 45.0, "ne": 45.0, "north-east": 45.0,
    "east": 90.0, "e": 90.0,
    "southeast": 135.0, "se": 135.0, "south-east": 135.0,
    "south": 180.0, "s": 180.0,
    "southwest": 225.0, "sw": 225.0, "south-west": 225.0,
    "west": 270.0, "w": 270.0,
    "northwest": 315.0, "nw": 315.0, "north-west": 315.0,
}


def cardinal_to_bearing(direction: str) -> float | None:
    """Convert a cardinal direction string to degrees (0=N, 90=E, …)."""
    return _CARDINAL_BEARINGS.get(direction.strip().lower())


def bearing_label(deg: float) -> str:
    """Convert bearing degrees back to a human-readable label."""
    directions = [
        "north", "northeast", "east", "southeast",
        "south", "southwest", "west", "northwest",
    ]
    idx = round(deg / 45) % 8
    return directions[idx]


# ─── Core geodesic computations ─────────────────────────────────────────────

def destination_point(
    origin_lat: float,
    origin_lon: float,
    bearing_deg: float,
    distance_km: float,
) -> tuple[float, float]:
    """Return (lat, lon) of a point that is *distance_km* from the origin
    along *bearing_deg* (geodesic, WGS-84).
    """
    lon2, lat2, _ = _geod.fwd(origin_lon, origin_lat, bearing_deg, distance_km * 1000)
    return float(lat2), float(lon2)


def _interpolate_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    n_points: int = 32,
) -> list[tuple[float, float]]:
    """Return n intermediate (lon, lat) points along the geodesic line."""
    pts = _geod.npts(origin_lon, origin_lat, dest_lon, dest_lat, n_points)
    coords = [(origin_lon, origin_lat)] + pts + [(dest_lon, dest_lat)]
    return coords  # list of (lon, lat) for Shapely/GeoJSON


def build_corridor(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    radius_km: float = 5.0,
) -> Any:  # Shapely Polygon
    """Build a buffered corridor polygon along the route.

    The buffer is computed in a local azimuthal equidistant projection
    centred on the route midpoint so the radius is accurate in metres.
    """
    from pyproj import Transformer
    from shapely.ops import transform as shp_transform

    coords_lonlat = _interpolate_route(origin_lat, origin_lon, dest_lat, dest_lon)
    line_wgs84 = LineString(coords_lonlat)

    mid_lon = (origin_lon + dest_lon) / 2
    mid_lat = (origin_lat + dest_lat) / 2
    aeqd_crs = (
        f"+proj=aeqd +lat_0={mid_lat} +lon_0={mid_lon} "
        f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs("EPSG:4326", aeqd_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(aeqd_crs, "EPSG:4326", always_xy=True)

    line_proj = shp_transform(to_aeqd.transform, line_wgs84)
    buffered_proj = line_proj.buffer(radius_km * 1000, cap_style=2)  # flat caps
    corridor_wgs84 = shp_transform(to_wgs84.transform, buffered_proj)
    return corridor_wgs84


def corridor_to_geojson_feature(polygon: Any, meta: dict | None = None) -> dict:
    """Wrap a Shapely polygon as a GeoJSON Feature."""
    props = {"layer": "corridor", "search_radius_km": meta.get("search_radius_km", 5.0)}
    if meta:
        props.update(meta)
    return {
        "type": "Feature",
        "geometry": mapping(polygon),
        "properties": props,
    }


def route_to_geojson_feature(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    meta: dict | None = None,
) -> dict:
    """Wrap the route as a GeoJSON LineString Feature."""
    coords = _interpolate_route(origin_lat, origin_lon, dest_lat, dest_lon)
    props = {"layer": "route"}
    if meta:
        props.update(meta)
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": props,
    }


def hotspot_to_geojson_feature(
    lat: float,
    lon: float,
    object_class: str,
    count: int,
    confidence_avg: float,
    distance_from_start_km: float,
) -> dict:
    """Wrap a hotspot cluster as a GeoJSON Point Feature."""
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "layer": "hotspot",
            "object_class": object_class,
            "count": count,
            "confidence_avg": round(confidence_avg, 3),
            "distance_from_start_km": round(distance_from_start_km, 1),
        },
    }


def distance_along_route_km(
    origin_lat: float,
    origin_lon: float,
    point_lat: float,
    point_lon: float,
) -> float:
    """Geodesic distance in km between two points."""
    _, _, dist_m = _geod.inv(origin_lon, origin_lat, point_lon, point_lat)
    return dist_m / 1000
