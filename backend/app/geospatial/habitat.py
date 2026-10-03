from __future__ import annotations

from app.geospatial.loaders import features_with_geometry, load_habitats


def habitat_overlaps(geometry) -> list[dict]:
    """Return demo habitat features (turtle nesting, coral reef, mangrove, ...)
    that intersect the given shapely geometry."""
    hits = []
    for feature, geom in features_with_geometry(load_habitats()):
        if geom.intersects(geometry):
            hits.append(feature)
    return hits


def species_habitat_overlaps(geometry, habitat_kind: str) -> list[dict]:
    return [f for f in habitat_overlaps(geometry) if f["properties"].get("habitat_kind") == habitat_kind]
