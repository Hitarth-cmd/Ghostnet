"""Debris database query for the chat pipeline.

Queries the SQLite Detection table, applies a Shapely corridor intersection
filter, groups results by object_class, and identifies hotspot clusters.

All spatial math is done by Shapely in Python — no PostGIS required.
The LLM receives ONLY the numbers produced here; it never invents data.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
from collections import defaultdict

from shapely.geometry import Point, shape

from app.chat.geometry_utils import distance_along_route_km, hotspot_to_geojson_feature
from app.chat.schemas import DebrisSummary, HotspotPoint

logger = logging.getLogger("ghostnet.chat.debris_query")

# Object class categorization
_GHOST_NET_CLASSES = {"suspected_ghost_gear"}
_DEBRIS_CLASSES = {"marine_debris", "plastic_debris", "floating_debris"}
# Everything else counts as "unknown"


def _object_class_bucket(cls: str) -> str:
    c = cls.lower()
    if c in _GHOST_NET_CLASSES:
        return "ghost_net"
    if c in _DEBRIS_CLASSES:
        return "debris"
    return "unknown"


def query_debris_in_corridor(
    db,                         # SQLAlchemy Session
    corridor_polygon,           # Shapely Polygon (WGS-84)
    origin_lat: float,
    origin_lon: float,
    date_iso: str | None = None,
    date_tolerance_days: int = 7,
) -> DebrisSummary:
    """Return debris counts and hotspots for detections inside the corridor.

    Parameters
    ----------
    db :
        An open SQLAlchemy session.
    corridor_polygon :
        Shapely Polygon representing the buffered route corridor (WGS-84).
    origin_lat, origin_lon :
        Departure point (used to compute distance-from-start for hotspots).
    date_iso :
        Target date in 'YYYY-MM-DD' format. If provided, detections are
        filtered to that date. If no detections exist for that exact date,
        the nearest date within *date_tolerance_days* is used.
    date_tolerance_days :
        How many days before/after *date_iso* to search if the target date
        has no data (default 7).

    Returns
    -------
    DebrisSummary
        Contains counts, hotspots (up to 5), and data-source metadata.
    """
    from app.models.detection import Detection

    # Compute corridor bounding box for a fast pre-filter
    minx, miny, maxx, maxy = corridor_polygon.bounds

    # ── Step 1: bounding-box pre-filter via SQLAlchemy ───────────────────
    rows = (
        db.query(Detection)
        .filter(
            Detection.latitude >= miny,
            Detection.latitude <= maxy,
            Detection.longitude >= minx,
            Detection.longitude <= maxx,
        )
        .all()
    )

    # ── Step 2: exact Shapely intersection ───────────────────────────────
    inside = []
    for det in rows:
        pt = Point(det.longitude, det.latitude)
        if corridor_polygon.contains(pt):
            inside.append(det)

    # ── Step 3: date filter ───────────────────────────────────────────────
    data_date: str | None = None
    nearest_available_date: str | None = None

    if date_iso is not None:
        target = dt.date.fromisoformat(date_iso)
        date_matched = [d for d in inside if d.timestamp.date() == target]

        if date_matched:
            inside = date_matched
            data_date = date_iso
        else:
            # Find nearest available date within tolerance
            available_dates = sorted({d.timestamp.date() for d in inside})
            if available_dates:
                closest = min(available_dates, key=lambda d: abs((d - target).days))
                if abs((closest - target).days) <= date_tolerance_days:
                    nearest_available_date = closest.isoformat()
                    inside = [d for d in inside if d.timestamp.date() == closest]
                    data_date = closest.isoformat()
                else:
                    # No data within tolerance — return empty summary
                    return DebrisSummary(
                        total_debris=0,
                        ghost_nets=0,
                        suspected_ghost_gear=0,
                        other_debris=0,
                        unknown_objects=0,
                        hotspots=[],
                        data_date=date_iso,
                        nearest_available_date=None,
                        data_source="OceanGuard Detection Database",
                    )
            else:
                data_date = None
    else:
        # No date filter — use all matching detections
        data_date = None

    # ── Step 4: count by category ─────────────────────────────────────────
    ghost_nets = 0
    suspected_ghost = 0
    other_debris = 0
    unknown_objects = 0

    bucket_groups: dict[str, list] = defaultdict(list)

    for det in inside:
        bucket = _object_class_bucket(det.object_class)
        if bucket == "ghost_net":
            ghost_nets += 1
            suspected_ghost += 1
        elif bucket == "debris":
            other_debris += 1
        else:
            unknown_objects += 1
        bucket_groups[det.object_class].append(det)

    total = len(inside)

    # ── Step 5: hotspot clustering (simple grid-cell grouping) ───────────
    hotspots = _build_hotspots(inside, origin_lat, origin_lon, max_clusters=5)

    return DebrisSummary(
        total_debris=total,
        ghost_nets=ghost_nets,
        suspected_ghost_gear=suspected_ghost,
        other_debris=other_debris,
        unknown_objects=unknown_objects,
        hotspots=hotspots,
        data_date=data_date,
        nearest_available_date=nearest_available_date,
        data_source="OceanGuard Detection Database",
    )


def _build_hotspots(
    detections: list,
    origin_lat: float,
    origin_lon: float,
    grid_size_deg: float = 0.2,
    max_clusters: int = 5,
) -> list[HotspotPoint]:
    """Simple grid-cell clustering: group detections by 0.2° cell, return top N by count."""
    cells: dict[tuple, list] = defaultdict(list)
    for det in detections:
        cell = (
            round(det.latitude / grid_size_deg) * grid_size_deg,
            round(det.longitude / grid_size_deg) * grid_size_deg,
        )
        cells[cell].append(det)

    # Sort by cell count descending
    sorted_cells = sorted(cells.items(), key=lambda x: len(x[1]), reverse=True)

    result = []
    for (cell_lat, cell_lon), cell_dets in sorted_cells[:max_clusters]:
        # Centre of mass
        avg_lat = sum(d.latitude for d in cell_dets) / len(cell_dets)
        avg_lon = sum(d.longitude for d in cell_dets) / len(cell_dets)
        avg_conf = sum(d.confidence for d in cell_dets) / len(cell_dets)
        # Most common object class in this cell
        class_counts: dict[str, int] = defaultdict(int)
        for d in cell_dets:
            class_counts[d.object_class] += 1
        dominant_class = max(class_counts, key=class_counts.__getitem__)
        dist_km = distance_along_route_km(origin_lat, origin_lon, avg_lat, avg_lon)

        result.append(HotspotPoint(
            lat=round(avg_lat, 5),
            lon=round(avg_lon, 5),
            object_class=dominant_class,
            count=len(cell_dets),
            confidence_avg=round(avg_conf, 3),
            distance_from_start_km=round(dist_km, 1),
        ))

    # Sort by distance from departure
    result.sort(key=lambda h: h.distance_from_start_km)
    return result


def hotspots_to_geojson_features(hotspots: list[HotspotPoint]) -> list[dict]:
    """Convert HotspotPoint list to GeoJSON Feature dicts."""
    return [
        hotspot_to_geojson_feature(
            h.lat, h.lon, h.object_class, h.count,
            h.confidence_avg, h.distance_from_start_km,
        )
        for h in hotspots
    ]
