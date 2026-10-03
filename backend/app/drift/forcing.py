"""
Forcing fields for the drift engine.

Two modes:

DEMO  - deterministic synthetic current + wind fields. Physically
        *plausible* (large-scale sinusoidal gyre component + a
        seasonal-ish drift term + small Ekman-style wind contribution),
        seeded so the same input always produces the same field. This is
        SOFTWARE TEST DATA, explicitly NOT a real ocean forecast - it
        exists so the whole downstream pipeline can be built, run and
        demonstrated without CMEMS/ERA5/GFS credentials.

LIVE  - adapters for real oceanographic forcing (CMEMS/Copernicus Marine,
        ERA5, GFS). No credentials are hard-coded; if the configured
        provider's credentials are absent the adapter raises
        LiveForcingUnavailableError so the caller can fall back to DEMO
        mode instead of silently returning wrong data.
"""
from __future__ import annotations

import math
import os
from abc import ABC, abstractmethod

from app.models.enums import ForcingMode


class LiveForcingUnavailableError(RuntimeError):
    pass


class ForcingProvider(ABC):
    mode: ForcingMode

    @abstractmethod
    def velocity_at(self, lat: float, lon: float, hours_since_start: float) -> tuple[float, float]:
        """Return (u, v) current velocity in m/s (eastward, northward)."""


class DemoForcingProvider(ForcingProvider):
    """Deterministic synthetic current + wind-driven (Ekman) field."""

    mode = ForcingMode.DEMO

    def __init__(self, seed_lat: float, seed_lon: float) -> None:
        # Seed the field's phase on the detection location so different
        # detections get visually distinct, but individually reproducible,
        # synthetic flow patterns.
        self._phase = (seed_lat * 13.37 + seed_lon * 7.11) % (2 * math.pi)

    def velocity_at(self, lat: float, lon: float, hours_since_start: float) -> tuple[float, float]:
        t = hours_since_start / 24.0  # in days

        # Large-scale gyre-like rotational component (bounded ~0.15 m/s).
        gyre_u = 0.12 * math.sin(math.radians(lat) * 2 + self._phase + 0.15 * t)
        gyre_v = 0.10 * math.cos(math.radians(lon) * 2 + self._phase - 0.10 * t)

        # Slow monsoon-like background drift, direction flips seasonally
        # in a deterministic (not random) fashion tied to time-of-year.
        monsoon_strength = 0.06 * math.sin(2 * math.pi * (t / 180.0))
        monsoon_u = monsoon_strength
        monsoon_v = 0.03 * math.cos(2 * math.pi * (t / 180.0))

        # Small Ekman-style wind-driven veer (constant synthetic 5 m/s
        # trade wind rotated ~45 degrees to the right in the northern
        # hemisphere, left in the southern hemisphere).
        wind_speed = 5.0
        ekman_factor = 0.02  # fraction of wind speed expressed at the surface
        veer_sign = 1.0 if lat >= 0 else -1.0
        veer = math.radians(45.0) * veer_sign
        wind_u = ekman_factor * wind_speed * math.cos(veer)
        wind_v = ekman_factor * wind_speed * math.sin(veer)

        u = gyre_u + monsoon_u + wind_u
        v = gyre_v + monsoon_v + wind_v
        return u, v


class CMEMSForcingProvider(ForcingProvider):
    """Adapter for Copernicus Marine Service current data (LIVE mode)."""

    mode = ForcingMode.LIVE

    def __init__(self) -> None:
        self.username = os.environ.get("CMEMS_USERNAME", "")
        self.password = os.environ.get("CMEMS_PASSWORD", "")
        if not self.username or not self.password:
            raise LiveForcingUnavailableError(
                "CMEMS_USERNAME/CMEMS_PASSWORD are not set. Configure Copernicus "
                "Marine credentials as environment variables, or use "
                "OCEAN_DATA_PROVIDER=demo."
            )

    def velocity_at(self, lat: float, lon: float, hours_since_start: float) -> tuple[float, float]:  # pragma: no cover
        raise NotImplementedError(
            "CMEMS live forcing requires the copernicusmarine client and network "
            "access to Copernicus Marine Service, not available in this "
            "environment. Implement this method against the copernicusmarine "
            "Python client once credentials and network access are available."
        )


def get_forcing_provider(mode: str, seed_lat: float, seed_lon: float) -> ForcingProvider:
    if mode == "live":
        try:
            return CMEMSForcingProvider()
        except LiveForcingUnavailableError:
            # Explicit, visible fallback - never silently mislabel demo
            # data as live.
            return DemoForcingProvider(seed_lat, seed_lon)
    return DemoForcingProvider(seed_lat, seed_lon)
