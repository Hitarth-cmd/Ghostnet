from __future__ import annotations

from app.geospatial.loaders import features_with_geometry, load_protected_areas


def protected_area_overlaps(geometry) -> list[dict]:
    """Return demo MPA features that intersect the given shapely geometry."""
    hits = []
    for feature, geom in features_with_geometry(load_protected_areas()):
        if geom.intersects(geometry):
            hits.append(feature)
    return hits
