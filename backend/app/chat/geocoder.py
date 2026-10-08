"""Gujarat coastal port geocoder.

Priority order:
1. Local lookup table (instant, no network, covers major Gujarat/Arabian Sea ports)
2. Nominatim (OpenStreetMap) — free, no API key required
3. Raise a descriptive error if both fail

The lookup table keys are normalized lower-case strings; fuzzy matching is
used so "Gulf of Kutch", "kutch", and "Kandla Port" all resolve to the same
coordinate.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import json
import logging

logger = logging.getLogger("ghostnet.chat.geocoder")

# ─────────────────────────────────────────────────────────────────────────────
# Local lookup table – Gujarat/Arabian Sea focus + key Indian Ocean locations
# ─────────────────────────────────────────────────────────────────────────────
_LOOKUP: dict[str, tuple[float, float]] = {
    # Gulf of Kutch
    "gulf of kutch":        (22.60, 69.50),
    "kutch":                (22.60, 69.50),
    "gulf kutch":           (22.60, 69.50),

    # Major Gujarat ports
    "kandla":               (23.03, 70.22),
    "kandla port":          (23.03, 70.22),
    "deendayal port":       (23.03, 70.22),
    "mundra":               (22.84, 69.71),
    "mundra port":          (22.84, 69.71),
    "okha":                 (22.47, 69.07),
    "okha port":            (22.47, 69.07),
    "porbandar":            (21.64, 69.61),
    "veraval":              (20.91, 70.36),
    "pipavav":              (20.91, 71.51),
    "hazira":               (21.11, 72.64),
    "surat":                (21.17, 72.83),
    "dahej":                (21.70, 72.55),
    "gopnath":              (21.37, 72.21),

    # Saurashtra coast
    "jamnagar":             (22.47, 70.06),
    "salaya":               (22.32, 69.60),
    "bedi port":            (22.54, 70.06),
    "sikka":                (22.43, 69.86),
    "navlakhi":             (22.96, 70.46),
    "mandvi":               (22.83, 69.36),
    "dwarka":               (22.24, 68.97),

    # Gulf of Khambhat (Cambay)
    "gulf of khambhat":     (21.00, 72.00),
    "gulf of cambay":       (21.00, 72.00),
    "khambhat":             (22.32, 72.62),
    "alang":                (21.41, 72.18),
    "bhavnagar":            (21.77, 72.15),

    # Mumbai / Maharashtra gateway
    "mumbai":               (18.93, 72.84),
    "nhava sheva":          (18.95, 72.95),
    "jawaharlal nehru port":(18.95, 72.95),
    "jnpt":                 (18.95, 72.95),
    "ratnagiri":            (16.99, 73.30),

    # Lakshadweep / offshore
    "lakshadweep":          (10.57, 72.64),
    "kavaratti":            (10.57, 72.64),

    # Generic references
    "arabian sea":          (19.00, 66.00),
    "indian ocean":         (10.00, 75.00),
}

# Alias set: terms that should map to another canonical key
_ALIASES: dict[str, str] = {
    "gulf of kachh":        "gulf of kutch",
    "rann of kutch":        "gulf of kutch",
    "mundra terminal":      "mundra",
    "mundra lpg":           "mundra",
    "sikka terminal":       "sikka",
}


def _normalize(text: str) -> str:
    """Lower-case and strip extra whitespace/punctuation."""
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


def _lookup_local(query: str) -> tuple[float, float] | None:
    key = _normalize(query)
    # Alias resolution
    key = _ALIASES.get(key, key)
    # Exact match
    if key in _LOOKUP:
        return _LOOKUP[key]
    # Substring match — find the longest key that is a substring of the query
    candidates = [(k, v) for k, v in _LOOKUP.items() if k in key]
    if candidates:
        best = max(candidates, key=lambda x: len(x[0]))
        return best[1]
    # Reverse substring match — query is a substring of a key
    candidates = [(k, v) for k, v in _LOOKUP.items() if key in k]
    if candidates:
        best = max(candidates, key=lambda x: len(x[0]))
        return best[1]
    return None


def _lookup_nominatim(query: str) -> tuple[float, float] | None:
    """Fall back to OpenStreetMap Nominatim (no API key required)."""
    encoded = urllib.parse.quote(query + ", India")
    url = (
        f"https://nominatim.openstreetmap.org/search"
        f"?q={encoded}&format=json&limit=1&addressdetails=0"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OceanGuard-ChatBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:
        logger.warning("Nominatim lookup failed for %r: %s", query, exc)
    return None


def geocode(place_name: str) -> tuple[float, float]:
    """Return (lat, lon) for a place name.

    Raises ValueError if the location cannot be resolved.
    """
    if not place_name or not place_name.strip():
        raise ValueError("Empty place name — cannot geocode.")

    coords = _lookup_local(place_name)
    if coords:
        logger.debug("Geocoded %r from local table → %s", place_name, coords)
        return coords

    coords = _lookup_nominatim(place_name)
    if coords:
        logger.debug("Geocoded %r via Nominatim → %s", place_name, coords)
        return coords

    raise ValueError(
        f"Could not geocode '{place_name}'. "
        "Try a major Gujarat port name such as 'Mundra', 'Kandla', or 'Okha'."
    )


def list_known_ports() -> list[str]:
    """Return a sorted list of known port/place names (for suggestion chips)."""
    return sorted({k.title() for k in _LOOKUP if len(k) > 4})
