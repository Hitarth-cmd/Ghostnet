from __future__ import annotations

from shapely.geometry import shape


def intersection_area_ratio(geometry_a: dict, geometry_b: dict) -> float:
    """Fraction (0-1) of geometry_a's area that overlaps geometry_b."""
    ga, gb = shape(geometry_a), shape(geometry_b)
    if ga.area == 0:
        return 1.0 if ga.intersects(gb) else 0.0
    return round(ga.intersection(gb).area / ga.area, 4)


def polygons_intersect(geometry_a: dict, geometry_b: dict) -> bool:
    return shape(geometry_a).intersects(shape(geometry_b))


def line_intersects_polygon(line_geometry: dict, polygon_geometry: dict) -> bool:
    return shape(line_geometry).intersects(shape(polygon_geometry))
