"""
Sentinel2ModelProvider - the integration point for the real trained
marine-debris segmentation model.

This module implements everything that is NOT the model itself:

    segmentation mask -> connected components -> pixel coords
        -> geographic coords (via the GeoTIFF's own CRS + affine transform)
        -> Shapely geometries -> DetectionRecord objects

That conversion pipeline is fully implemented and unit-tested (see
tests/test_model_provider_geo.py) using synthetic masks, so it works
correctly regardless of which model produces the mask.

The one piece this module intentionally does NOT fake is model inference
itself. `_run_model_inference` raises ModelNotConfiguredError until you
point MODEL_CHECKPOINT_PATH at your real trained checkpoint and implement
`_load_model` / `_run_model_inference` for your model's actual framework
(PyTorch, TensorFlow, ONNX, ...). See README.md "Model integration".
"""
from __future__ import annotations

import datetime as dt
import os
import uuid
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from app.detection.providers.base import DetectionProvider, DetectionRecord
from app.models.enums import ObjectClass


class ModelNotConfiguredError(RuntimeError):
    """Raised when MODEL_PROVIDER=sentinel2 but no real checkpoint is installed."""


@dataclass
class GeoRaster:
    """Minimal georeferencing info needed to convert pixels -> lat/lon."""

    transform: "object"  # affine.Affine (from rasterio)
    crs: "object"  # rasterio.crs.CRS
    width: int
    height: int


def load_geotiff(path: str) -> tuple[np.ndarray, GeoRaster]:
    """Read a GeoTIFF's first band plus its CRS/transform/bounds/size."""
    import rasterio

    if not os.path.exists(path):
        raise FileNotFoundError(f"GeoTIFF not found: {path}")

    with rasterio.open(path) as src:
        band = src.read(1)
        raster = GeoRaster(transform=src.transform, crs=src.crs, width=src.width, height=src.height)
    return band, raster


def pixel_to_lonlat(row: int, col: int, raster: GeoRaster) -> tuple[float, float]:
    """
    Convert a (row, col) pixel coordinate to WGS84 (lon, lat).

    Uses the GeoTIFF's own affine transform to go pixel -> projected
    coordinate, then reprojects to EPSG:4326 if the source CRS differs.
    Never assumes lat/lon can be read directly from pixel indices.
    """
    import rasterio.warp
    from rasterio.crs import CRS

    x, y = raster.transform * (col + 0.5, row + 0.5)  # pixel centre -> projected coords
    wgs84 = CRS.from_epsg(4326)
    if raster.crs is not None and raster.crs != wgs84:
        xs, ys = rasterio.warp.transform(raster.crs, wgs84, [x], [y])
        return xs[0], ys[0]
    return x, y


def extract_detections_from_mask(
    mask: np.ndarray,
    raster: GeoRaster,
    scene_id: str,
    confidence_map: np.ndarray | None = None,
    min_pixel_area: int = 4,
    object_class: ObjectClass = ObjectClass.SUSPECTED_GHOST_GEAR,
) -> list[DetectionRecord]:
    """
    Connected-component extraction + pixel->geographic conversion.

    mask: binary (0/1) array, same shape as the source raster band.
    confidence_map: optional float array (same shape) with per-pixel model
        probability; if omitted, confidence defaults to 1.0 for every blob.
    """
    if mask.ndim != 2:
        raise ValueError("mask must be a 2D array")

    labeled, n_components = ndimage.label(mask > 0)
    records: list[DetectionRecord] = []

    # Approximate per-pixel ground area from the affine transform's pixel
    # size (in projected-CRS units, assumed metres for a projected CRS).
    pixel_area_m2 = abs(raster.transform.a) * abs(raster.transform.e)

    for component_id in range(1, n_components + 1):
        ys, xs = np.where(labeled == component_id)
        if len(ys) < min_pixel_area:
            continue

        centroid_row = float(np.mean(ys))
        centroid_col = float(np.mean(xs))
        lon, lat = pixel_to_lonlat(centroid_row, centroid_col, raster)

        if confidence_map is not None:
            confidence = float(np.mean(confidence_map[ys, xs]))
        else:
            confidence = 1.0

        # Build a simple polygon footprint from the pixel bounding box,
        # converting its four corners to geographic coordinates.
        row_min, row_max = int(ys.min()), int(ys.max())
        col_min, col_max = int(xs.min()), int(xs.max())
        corners_px = [
            (row_min, col_min),
            (row_min, col_max),
            (row_max, col_max),
            (row_max, col_min),
            (row_min, col_min),
        ]
        ring = [pixel_to_lonlat(r, c, raster) for r, c in corners_px]

        records.append(
            DetectionRecord(
                external_id=f"S2-{scene_id}-{component_id:04d}-{uuid.uuid4().hex[:6]}",
                latitude=lat,
                longitude=lon,
                confidence=round(confidence, 4),
                object_class=object_class,
                timestamp=dt.datetime.utcnow(),
                source="sentinel2-model",
                scene_id=scene_id,
                geometry={"type": "Polygon", "coordinates": [[[c[0], c[1]] for c in ring]]},
                area_m2=round(len(ys) * pixel_area_m2, 2),
            )
        )

    return records


class Sentinel2ModelProvider(DetectionProvider):
    """
    Real-model detection provider.

    Swap this in with MODEL_PROVIDER=sentinel2 once a trained checkpoint
    is installed. Until then it raises ModelNotConfiguredError with clear
    instructions rather than silently returning empty or fabricated
    results - the platform must never pretend to have run inference it
    did not actually run.
    """

    name = "sentinel2"

    def __init__(self, checkpoint_path: str | None = None) -> None:
        self.checkpoint_path = checkpoint_path or os.environ.get("MODEL_CHECKPOINT_PATH", "")
        self._model = None

    def _ensure_configured(self) -> None:
        if not self.checkpoint_path or not os.path.exists(self.checkpoint_path):
            raise ModelNotConfiguredError(
                "MODEL_PROVIDER=sentinel2 but no trained checkpoint was found. "
                "Set MODEL_CHECKPOINT_PATH to your trained model file and implement "
                "Sentinel2ModelProvider._load_model / _run_model_inference for your "
                "model's framework. See README.md 'Model integration' for the exact "
                "steps. Until then, use MODEL_PROVIDER=mock."
            )

    def _load_model(self):  # pragma: no cover - integration point
        """
        Load your trained checkpoint here (e.g. torch.load(...).eval()).
        Left unimplemented on purpose: this repository does not ship or
        fabricate a trained marine-debris segmentation model.
        """
        raise ModelNotConfiguredError(
            "Sentinel2ModelProvider._load_model is not implemented. "
            "Implement model loading for your framework, then remove this guard."
        )

    def _run_model_inference(self, image_band: np.ndarray) -> tuple[np.ndarray, np.ndarray]:  # pragma: no cover
        """
        Run your trained model on `image_band` and return (binary_mask,
        confidence_map), both same shape as image_band. Left unimplemented
        on purpose - see class docstring.
        """
        raise ModelNotConfiguredError(
            "Sentinel2ModelProvider._run_model_inference is not implemented."
        )

    def run_on_geotiff(self, path: str) -> list[DetectionRecord]:
        self._ensure_configured()
        if self._model is None:
            self._model = self._load_model()

        band, raster = load_geotiff(path)
        mask, confidence_map = self._run_model_inference(band)
        scene_id = os.path.splitext(os.path.basename(path))[0]
        return extract_detections_from_mask(mask, raster, scene_id, confidence_map=confidence_map)

    # --- DetectionProvider interface -----------------------------------
    def detect(self, **kwargs) -> list[DetectionRecord]:
        geotiff_path = kwargs.get("geotiff_path")
        if not geotiff_path:
            raise ValueError("Sentinel2ModelProvider.detect requires geotiff_path=...")
        return self.run_on_geotiff(geotiff_path)

    def get_detection(self, external_id: str) -> DetectionRecord | None:
        self._ensure_configured()
        return None

    def list_detections(self) -> list[DetectionRecord]:
        self._ensure_configured()
        return []
