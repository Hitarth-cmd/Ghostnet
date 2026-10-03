from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Particle:
    lat: float
    lon: float


def seed_particles(
    lat: float,
    lon: float,
    count: int,
    seed_key: str,
    spread_deg: float = 0.03,
) -> list[Particle]:
    """
    Deterministically seed an ensemble of particles around a detection
    point. `seed_key` (e.g. the detection's external_id) makes the
    ensemble reproducible for the same detection across runs.
    """
    rng = random.Random(seed_key)
    particles = []
    for _ in range(count):
        dlat = rng.uniform(-spread_deg, spread_deg)
        dlon = rng.uniform(-spread_deg, spread_deg)
        particles.append(Particle(lat=lat + dlat, lon=lon + dlon))
    return particles
