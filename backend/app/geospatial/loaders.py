from __future__ import annotations

import json
import os
from functools import lru_cache

from shapely.geometry import shape

_DATA_ROOT = os.environ.get(
    "GHOSTNET_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "demo"),
)


def _load_geojson(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_protected_areas() -> dict:
    return _load_geojson(os.path.join(_DATA_ROOT, "protected_areas", "mpas.geojson"))


@lru_cache
def load_habitats() -> dict:
    return _load_geojson(os.path.join(_DATA_ROOT, "habitats", "habitats.geojson"))


@lru_cache
def load_coastline() -> dict:
    return _load_geojson(os.path.join(_DATA_ROOT, "coastline", "coastline.geojson"))


def features_with_geometry(collection: dict) -> list[tuple[dict, "object"]]:
    """Return [(feature, shapely_geometry), ...] for a FeatureCollection."""
    return [(f, shape(f["geometry"])) for f in collection["features"]]
