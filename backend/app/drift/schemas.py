from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class DriftRequest(BaseModel):
    detection_id: str
    latitude: float
    longitude: float
    start_time: dt.datetime
    forecast_hours: tuple[int, ...] = (24, 48, 72)
    particle_count: int = 60
    ocean_data_provider: str = "demo"


class HorizonResult(BaseModel):
    forecast_hour: int
    timestamp: dt.datetime
    mean_latitude: float
    mean_longitude: float
    position_geometry: dict
    uncertainty_geometry: dict
    particle_geometry: dict


class DriftResult(BaseModel):
    detection_id: str
    mode: str
    source: str = "ghostnet-drift-engine"
    horizons: list[HorizonResult]
