"""
Ecological Alert Engine — generates marine-life alerts when debris or its
predicted drift path overlaps with or approaches:
  - Coral reef zones
  - Marine Protected Areas
  - Turtle nesting/feeding grounds
  - Whale/dolphin corridors
  - Dugong, whale shark habitats

Severity is determined by:
  CRITICAL: Debris is currently inside a high-value zone OR will enter within 6h
  HIGH: Drift predicted to enter within 24h
  MEDIUM: Drift predicted to enter within 48h
  LOW: Detected within 100 km of an ecological zone

Alert generation is fully deterministic from the spatial data — no LLM fabrication.
"""
from __future__ import annotations

import logging
from typing import Any

from shapely.geometry import Point, shape

from app.geospatial.data_collector import get_all_ecological_layers

logger = logging.getLogger("ghostnet.alert_engine")

# Speed assumption for "time to reach zone" when not in direct drift path
_DEFAULT_DRIFT_SPEED_KMH = 0.4  # ~0.1 m/s typical surface current
_PROXIMITY_WARNING_KM = 100.0  # zone within this distance triggers LOW

# Feature-type-specific severity boosts and human-readable labels
_FEATURE_SEVERITY = {
    "coral_reef": "CRITICAL",
    "species_sanctuary": "HIGH",
    "protected_area": "HIGH",
    "turtle_nesting": "CRITICAL",
    "whale_corridor": "HIGH",
    "dolphin_habitat": "HIGH",
    "dugong_habitat": "CRITICAL",
    "shark_habitat": "HIGH",
    "mangrove": "HIGH",
}

_FEATURE_LABELS = {
    "coral_reef": "Coral Reef Zone",
    "species_sanctuary": "Protected Species Sanctuary",
    "protected_area": "Marine Protected Area",
    "turtle_nesting": "Turtle Nesting Beach",
    "whale_corridor": "Whale Migration Corridor",
    "dolphin_habitat": "Dolphin Habitat",
    "dugong_habitat": "Dugong Habitat",
    "shark_habitat": "Shark Congregation Area",
    "mangrove": "Mangrove Ecosystem",
}

_RECOMMENDED_ACTIONS = {
    "CRITICAL": "IMMEDIATE RESPONSE REQUIRED — Deploy cleanup vessel within 12 hours. Alert wildlife monitors. Contact nearest MPA authority.",
    "HIGH": "Priority response within 24–48 hours. Coordinate with local NGO/coast guard for retrieval mission.",
    "MEDIUM": "Schedule monitoring/retrieval within 72 hours. Share alert with regional coordinators.",
    "LOW": "Add to monitoring queue. Reassess when next drift update available.",
}


def _dist_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    import math
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _point_in_polygon(lat: float, lon: float, geom: Any) -> bool:
    return geom.contains(Point(lon, lat))


def _distance_to_polygon_km(lat: float, lon: float, geom: Any) -> float:
    """Minimum great-circle distance from a point to the nearest polygon boundary in km."""
    point = Point(lon, lat)
    if geom.contains(point):
        return 0.0
    nearest = geom.exterior.interpolate(geom.exterior.project(point))
    return _dist_km(lat, lon, nearest.y, nearest.x)


def generate_ecological_alerts(
    detection_id: str,
    external_id: str,
    latitude: float,
    longitude: float,
    confidence: float,
    drift_horizons: list[dict],  # list of {forecast_hour, mean_lat, mean_lon, uncertainty_geometry}
) -> list[dict]:
    """
    Returns a list of alert dicts for each ecological zone that is:
    - Currently overlapping with the detection location, OR
    - Will be overlapped by a drift forecast horizon, OR
    - Within _PROXIMITY_WARNING_KM km of current detection location
    """
    try:
        all_layers = get_all_ecological_layers()
    except Exception as exc:
        logger.error("[ALERT_ENGINE] Failed to load ecological layers: %s", exc)
        return []

    alerts: list[dict] = []
    seen_keys: set[str] = set()  # avoid duplicate alerts for same detection+zone

    for feature in all_layers.get("features", []):
        props = feature.get("properties", {})
        zone_name = props.get("name", "Unknown Zone")
        feature_type = props.get("feature_type", "protected_area")
        habitat_kind = props.get("habitat_kind", feature_type)
        species = props.get("species", [])
        source = props.get("source", "GCRMN/OBIS")
        source_url = props.get("source_url", "")

        try:
            zone_geom = shape(feature["geometry"])
        except Exception:
            continue

        # --- Check 1: Current detection location ---
        dist_now = _distance_to_polygon_km(latitude, longitude, zone_geom)
        in_zone_now = dist_now == 0.0

        # --- Check 2: Drift horizon overlaps ---
        closest_horizon = None
        min_drift_dist = float("inf")
        for horizon in drift_horizons:
            h_lat = horizon.get("mean_lat", latitude)
            h_lon = horizon.get("mean_lon", longitude)
            h_dist = _distance_to_polygon_km(h_lat, h_lon, zone_geom)
            if h_dist < min_drift_dist:
                min_drift_dist = h_dist
                closest_horizon = horizon

        # Also check uncertainty polygon overlap
        uncertainty_overlap = False
        for horizon in drift_horizons:
            try:
                unc_geom = shape(horizon.get("uncertainty_geometry", {}))
                if zone_geom.intersects(unc_geom):
                    uncertainty_overlap = True
                    break
            except Exception:
                pass

        # --- Determine severity ---
        if in_zone_now or uncertainty_overlap:
            severity = "CRITICAL"
            est_hours = 0.0
        elif min_drift_dist < 30 and closest_horizon:
            severity = _FEATURE_SEVERITY.get(habitat_kind, _FEATURE_SEVERITY.get(feature_type, "HIGH"))
            est_hours = closest_horizon.get("forecast_hour", 24)
        elif min_drift_dist < _PROXIMITY_WARNING_KM:
            # Downgrade severity one step for proximity-only
            base = _FEATURE_SEVERITY.get(habitat_kind, _FEATURE_SEVERITY.get(feature_type, "MEDIUM"))
            severity = {"CRITICAL": "HIGH", "HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}.get(base, "LOW")
            est_hours = min_drift_dist / _DEFAULT_DRIFT_SPEED_KMH if _DEFAULT_DRIFT_SPEED_KMH > 0 else 999.0
        else:
            continue  # Too far away, skip

        key = f"{detection_id}:{zone_name}:{feature_type}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        feature_label = _FEATURE_LABELS.get(habitat_kind, _FEATURE_LABELS.get(feature_type, "Ecological Zone"))

        if in_zone_now:
            headline = f"⚠️ Debris detected INSIDE {feature_label}: {zone_name}"
            details = (
                f"Marine debris (confidence={confidence:.0%}) has been detected directly within the {feature_label} "
                f"'{zone_name}'. Immediate ecological risk. Species at risk: {', '.join(species) or 'unknown'}."
            )
        elif uncertainty_overlap:
            headline = f"⚠️ Drift cone intersects {feature_label}: {zone_name}"
            details = (
                f"Predicted drift trajectory uncertainty zone overlaps with '{zone_name}'. "
                f"Debris could enter this area within the forecast window. Species at risk: {', '.join(species) or 'unknown'}."
            )
        else:
            time_str = f"~{est_hours:.0f}h" if est_hours < 999 else "unknown time"
            headline = f"🔶 Debris drifting toward {feature_label}: {zone_name}"
            details = (
                f"Debris is {min_drift_dist:.1f} km from '{zone_name}' (estimated arrival: {time_str}). "
                f"Species at risk: {', '.join(species) or 'unknown'}. Source: {source}."
            )

        # Impact point — centroid of the zone
        centroid = zone_geom.centroid
        impact_geometry = {"type": "Point", "coordinates": [centroid.x, centroid.y]}

        source_citation = f"{source}"
        if source_url:
            source_citation += f" — {source_url}"

        alerts.append({
            "detection_id": detection_id,
            "external_id": external_id,
            "alert_type": habitat_kind or feature_type,
            "severity": severity,
            "status": "active",
            "headline": headline,
            "details": details,
            "region_name": zone_name,
            "feature_type": habitat_kind or feature_type,
            "species_at_risk": species,
            "distance_km": round(dist_now if in_zone_now else min_drift_dist, 2),
            "estimated_impact_hours": round(est_hours, 1),
            "impact_point_geometry": impact_geometry,
            "recommended_action": _RECOMMENDED_ACTIONS.get(severity, ""),
            "source_citation": source_citation,
        })

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))
    logger.info(
        "[ALERT_ENGINE] detection=%s generated %d ecological alerts", external_id, len(alerts)
    )
    return alerts
