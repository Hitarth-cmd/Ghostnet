from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.detection.earthengine_scanner import (
    get_detection_visuals,
    ingest_and_scan_all_regions,
)
from app.detection.earthengine_service import (
    DEFAULT_EE_PROJECT,
    OFFSHORE_REGIONS,
    get_earth_engine_status,
    scan_earth_engine_region,
)
from app.models.detection import Detection

router = APIRouter(prefix="/api/v1/earthengine", tags=["earthengine"])
logger = logging.getLogger("ghostnet.earthengine_api")


class ScanRequest(BaseModel):
    latitude: float = Field(..., description="Latitude of ocean observation target")
    longitude: float = Field(..., description="Longitude of ocean observation target")
    pixel_size_meters: float = Field(10.0, description="Spatial resolution in meters per pixel")
    plot_to_map: bool = Field(True, description="Whether to plot detected debris to live GIS map")


@router.get("/status")
def status() -> Dict[str, Any]:
    """
    Get Google Earth Engine connection status for project balmy-ocean-509105-v8.
    """
    return get_earth_engine_status()


@router.get("/regions")
def list_regions() -> Dict[str, Any]:
    """
    List pre-configured offshore marine observation regions.
    """
    return {
        "project_id": DEFAULT_EE_PROJECT,
        "regions": OFFSHORE_REGIONS,
    }


@router.post("/scan")
def scan_ocean_region(req: ScanRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Fetch Sentinel-2 multispectral satellite data from Earth Engine and run
    marine debris detection directly without uploading any local files.
    """
    return scan_earth_engine_region(
        latitude=req.latitude,
        longitude=req.longitude,
        pixel_size_meters=req.pixel_size_meters,
        plot_to_map=req.plot_to_map,
        db=db,
    )


@router.post("/sync-catalog")
def sync_earth_engine_catalog(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Ingest Sentinel-2 satellite data from Earth Engine (balmy-ocean-509105-v8),
    run real ViT-UNet++ model inference across Indian coastal hotspots,
    and update the database.
    """
    active_count = ingest_and_scan_all_regions(db, force=True)
    return {
        "status": "success",
        "message": f"Successfully synced {active_count} Sentinel-2 Earth Engine marine detections.",
        "project_id": DEFAULT_EE_PROJECT,
        "active_detections": active_count,
    }


@router.get("/preview/{detection_id}")
def get_satellite_preview(detection_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieve Sentinel-2 RGB quicklook, 11-class segmentation mask, and overlay
    for a specific detection.
    """
    det = db.query(Detection).filter(
        (Detection.id == detection_id) | (Detection.external_id == detection_id)
    ).one_or_none()

    if det is None:
        raise HTTPException(status_code=404, detail=f"Detection '{detection_id}' not found")

    cached = get_detection_visuals(det.external_id)
    if cached is not None:
        return cached

    # If not in cache, run quick scan on detection's coordinates to generate visuals
    res = scan_earth_engine_region(
        latitude=det.latitude,
        longitude=det.longitude,
        pixel_size_meters=10.0,
        plot_to_map=False,
        db=None,
    )
    return {
        "external_id": det.external_id,
        "scene_id": det.scene_id,
        "source": det.source,
        "summary": res["summary"],
        "class_breakdown": res["class_breakdown"],
        "visualizations": res["visualizations"],
    }
