from __future__ import annotations

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import from_origin

from app.detection.providers.model import GeoRaster, extract_detections_from_mask
from app.models.enums import ObjectClass


def _synthetic_raster(pixel_size_deg: float = 0.001) -> GeoRaster:
    # Top-left corner near the Goa coast, WGS84 CRS, small pixel size so
    # pixel<->degree math is easy to sanity check.
    transform = from_origin(72.0, 16.0, pixel_size_deg, pixel_size_deg)
    return GeoRaster(transform=transform, crs=CRS.from_epsg(4326), width=100, height=100)


def test_extract_detections_from_mask_finds_components():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:15, 10:15] = 1  # one 5x5 blob
    mask[50:53, 60:63] = 1  # one 3x3 blob

    raster = _synthetic_raster()
    detections = extract_detections_from_mask(mask, raster, scene_id="TEST-SCENE", min_pixel_area=4)

    assert len(detections) == 2
    for d in detections:
        assert -90 <= d.latitude <= 90
        assert -180 <= d.longitude <= 180
        assert d.object_class == ObjectClass.SUSPECTED_GHOST_GEAR
        assert d.source == "sentinel2-model"


def test_extract_detections_respects_min_pixel_area():
    mask = np.zeros((50, 50), dtype=np.uint8)
    mask[0:2, 0:2] = 1  # only 4 pixels

    raster = _synthetic_raster()
    detections = extract_detections_from_mask(mask, raster, scene_id="TEST-SCENE-2", min_pixel_area=10)
    assert len(detections) == 0


def test_pixel_to_lonlat_matches_transform_origin():
    from app.detection.providers.model import pixel_to_lonlat

    raster = _synthetic_raster(pixel_size_deg=0.01)
    lon, lat = pixel_to_lonlat(row=0, col=0, raster=raster)
    # Pixel (0,0)'s centre should be half a pixel south-east of the (72.0, 16.0) origin.
    assert abs(lon - (72.0 + 0.005)) < 1e-6
    assert abs(lat - (16.0 - 0.005)) < 1e-6
