from __future__ import annotations

import math
from dataclasses import dataclass

from app.drift.forcing import ForcingProvider, get_forcing_provider
from app.drift.particles import Particle, seed_particles

METERS_PER_DEGREE_LAT = 111_320.0


def _meters_per_degree_lon(lat_deg: float) -> float:
    return METERS_PER_DEGREE_LAT * max(math.cos(math.radians(lat_deg)), 1e-6)


@dataclass
class DriftRun:
    detection_id: str
    mode: str
    forcing: ForcingProvider
    particle_history: dict[int, list[Particle]]  # hour -> particle snapshot


def run_drift_simulation(
    detection_id: str,
    latitude: float,
    longitude: float,
    forecast_hours: tuple[int, ...] = (24, 48, 72),
    particle_count: int = 60,
    ocean_data_provider: str = "demo",
    step_hours: float = 1.0,
) -> DriftRun:
    """
    Advect an ensemble of particles from (latitude, longitude) forward in
    time through the configured forcing field, recording a snapshot of
    every particle's position at each requested forecast hour.

    This plays the same architectural role OpenDrift would (particle-based
    Lagrangian advection driven by a forcing field with DEMO/LIVE modes),
    implemented in pure Python so it runs with zero external
    dependencies / ocean-data downloads. The interface (inputs: lat, lon,
    timestamp, forecast duration, particle count -> outputs: particle
    trajectories, ensemble position, uncertainty geometry per horizon) is
    the contract; a real OpenDrift-backed engine can be substituted here
    without changing anything downstream.
    """
    forcing = get_forcing_provider(ocean_data_provider, latitude, longitude)
    particles = seed_particles(latitude, longitude, particle_count, seed_key=detection_id)

    max_hour = max(forecast_hours)
    history: dict[int, list[Particle]] = {0: [Particle(p.lat, p.lon) for p in particles]}

    elapsed = 0.0
    while elapsed < max_hour:
        step = min(step_hours, max_hour - elapsed)
        new_particles = []
        for p in particles:
            u, v = forcing.velocity_at(p.lat, p.lon, elapsed)
            dlat = (v * step * 3600.0) / METERS_PER_DEGREE_LAT
            dlon = (u * step * 3600.0) / _meters_per_degree_lon(p.lat)
            new_particles.append(Particle(lat=p.lat + dlat, lon=p.lon + dlon))
        particles = new_particles
        elapsed += step

        elapsed_rounded = round(elapsed, 6)
        if int(elapsed_rounded) in forecast_hours and float(int(elapsed_rounded)) == elapsed_rounded:
            history[int(elapsed_rounded)] = [Particle(p.lat, p.lon) for p in particles]

    # Guarantee every requested horizon has a snapshot even if float steps
    # didn't land exactly on it (defensive - step_hours=1.0 always lands
    # exactly for integer forecast_hours).
    for h in forecast_hours:
        if h not in history:
            history[h] = [Particle(p.lat, p.lon) for p in particles]

    mode = forcing.mode.value
    return DriftRun(detection_id=detection_id, mode=mode, forcing=forcing, particle_history=history)
