from __future__ import annotations

from shapely.geometry import MultiPoint, mapping

from app.drift.particles import Particle


def uncertainty_polygon(particles: list[Particle]) -> dict:
    """
    Convex hull of the particle ensemble at a given forecast horizon,
    representing the forecast/probability zone the debris plausibly
    occupies - NOT a guaranteed exact future position.
    """
    if len(particles) < 3:
        # Degenerate case: not enough particles for a polygon, fall back
        # to a tiny buffered point so the frontend always gets a polygon.
        pt = particles[0] if particles else Particle(0.0, 0.0)
        buffered = MultiPoint([(pt.lon, pt.lat)]).buffer(0.01)
        return mapping(buffered)

    coords = [(p.lon, p.lat) for p in particles]
    hull = MultiPoint(coords).convex_hull
    if hull.geom_type != "Polygon":
        hull = hull.buffer(0.005)
    return mapping(hull)


def ensemble_mean_position(particles: list[Particle]) -> tuple[float, float]:
    lat = sum(p.lat for p in particles) / len(particles)
    lon = sum(p.lon for p in particles) / len(particles)
    return lat, lon
