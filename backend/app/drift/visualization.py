from __future__ import annotations

from app.drift.schemas import DriftResult


def drift_result_to_geojson(result: DriftResult, origin_lat: float, origin_lon: float) -> dict:
    """
    Build a FeatureCollection with:
      - one LineString per horizon (origin -> ensemble-mean position at
        that horizon) named trajectory_24h / trajectory_48h / trajectory_72h
      - one uncertainty polygon per horizon
    Every feature carries detection_id, forecast_hour, timestamp, source,
    mode as required by the spec so the frontend can style/filter by them.
    """
    features = []
    for h in result.horizons:
        common_props = {
            "detection_id": result.detection_id,
            "forecast_hour": h.forecast_hour,
            "timestamp": h.timestamp.isoformat(),
            "source": result.source,
            "mode": result.mode,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[origin_lon, origin_lat], [h.mean_longitude, h.mean_latitude]],
                },
                "properties": {
                    **common_props,
                    "layer": f"trajectory_{h.forecast_hour}h",
                },
            }
        )
        features.append(
            {
                "type": "Feature",
                "geometry": h.uncertainty_geometry,
                "properties": {**common_props, "layer": "uncertainty_polygon"},
            }
        )
        features.append(
            {
                "type": "Feature",
                "geometry": h.position_geometry,
                "properties": {**common_props, "layer": "forecast_position"},
            }
        )

    return {"type": "FeatureCollection", "features": features}
