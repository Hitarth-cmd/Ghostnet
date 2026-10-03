from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class RiskFeatureInputs:
    detection_confidence: float  # 0-1, direct from detection
    protected_area_overlap: bool
    habitat_overlap: bool
    species_habitat_overlap: bool  # e.g. turtle/coral specific overlap
    distance_to_coastline_km: float
    forecast_uncertainty_area_km2: float
    scene_id: str = ""


def _deterministic_fishing_activity_index(scene_id: str) -> float:
    """
    DEMO fishing-activity proxy. Real deployments should replace this with
    an authoritative fishing-effort dataset (e.g. Global Fishing Watch).
    For the demo, this is a deterministic hash-derived value in [0, 1] so
    it is reproducible and clearly not a live feed.
    """
    if not scene_id:
        return 0.3
    digest = hashlib.sha256(scene_id.encode()).hexdigest()
    return (int(digest[:8], 16) % 1000) / 1000.0


def compute_raw_features(inputs: RiskFeatureInputs, coastline_proximity_max_km: float) -> dict[str, float]:
    trajectory_confidence = max(0.0, 1.0 - min(inputs.forecast_uncertainty_area_km2 / 500.0, 1.0))
    coastline_proximity = max(0.0, 1.0 - min(inputs.distance_to_coastline_km / coastline_proximity_max_km, 1.0))
    fishing_activity = _deterministic_fishing_activity_index(inputs.scene_id)
    forecast_uncertainty = min(inputs.forecast_uncertainty_area_km2 / 500.0, 1.0)

    return {
        "detection_confidence": round(inputs.detection_confidence, 4),
        "trajectory_confidence": round(trajectory_confidence, 4),
        "protected_area_overlap": 1.0 if inputs.protected_area_overlap else 0.0,
        "habitat_overlap": 1.0 if inputs.habitat_overlap else 0.0,
        "species_habitat_overlap": 1.0 if inputs.species_habitat_overlap else 0.0,
        "coastline_proximity": round(coastline_proximity, 4),
        "fishing_activity": round(fishing_activity, 4),
        "forecast_uncertainty": round(forecast_uncertainty, 4),
    }
