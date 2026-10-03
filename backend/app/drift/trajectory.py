from __future__ import annotations

import datetime as dt

from shapely.geometry import MultiPoint, Point, mapping

from app.drift.engine import run_drift_simulation
from app.drift.schemas import DriftRequest, DriftResult, HorizonResult
from app.drift.uncertainty import ensemble_mean_position, uncertainty_polygon


def forecast_drift(request: DriftRequest) -> DriftResult:
    """Run the drift engine and assemble a complete, per-horizon DriftResult."""
    run = run_drift_simulation(
        detection_id=request.detection_id,
        latitude=request.latitude,
        longitude=request.longitude,
        forecast_hours=request.forecast_hours,
        particle_count=request.particle_count,
        ocean_data_provider=request.ocean_data_provider,
    )

    horizons: list[HorizonResult] = []
    for hour in request.forecast_hours:
        particles = run.particle_history[hour]
        mean_lat, mean_lon = ensemble_mean_position(particles)
        position_geom = mapping(Point(mean_lon, mean_lat))
        uncertainty_geom = uncertainty_polygon(particles)
        particle_geom = mapping(MultiPoint([(p.lon, p.lat) for p in particles]))

        horizons.append(
            HorizonResult(
                forecast_hour=hour,
                timestamp=request.start_time + dt.timedelta(hours=hour),
                mean_latitude=mean_lat,
                mean_longitude=mean_lon,
                position_geometry=position_geom,
                uncertainty_geometry=uncertainty_geom,
                particle_geometry=particle_geom,
            )
        )

    return DriftResult(detection_id=request.detection_id, mode=run.mode, horizons=horizons)
