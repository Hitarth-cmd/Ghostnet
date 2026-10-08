from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.geospatial.loaders import load_coastline, load_habitats, load_protected_areas
from app.models.detection import Detection
from app.models.other import Trajectory

router = APIRouter(prefix="/api/v1/map", tags=["map"])


@router.get("/detections")
def map_detections(db: Session = Depends(get_db)) -> dict:
    detections = db.query(Detection).all()
    return {"type": "FeatureCollection", "features": [d.to_geojson_feature() for d in detections]}


@router.get("/trajectories")
def map_trajectories(db: Session = Depends(get_db)) -> dict:
    """All persisted drift trajectories/uncertainty zones across every analyzed detection."""
    features = []
    trajectories = db.query(Trajectory).all()
    detections_by_id = {d.id: d for d in db.query(Detection).all()}

    for t in trajectories:
        detection = detections_by_id.get(t.detection_id)
        if detection is None:
            continue
        common = {
            "detection_id": detection.external_id,
            "forecast_hour": t.forecast_hour,
            "timestamp": t.timestamp.isoformat(),
            "source": t.source,
            "mode": t.mode,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [detection.longitude, detection.latitude],
                        t.position_geometry["coordinates"],
                    ],
                },
                "properties": {**common, "layer": f"trajectory_{t.forecast_hour}h"},
            }
        )
        features.append(
            {"type": "Feature", "geometry": t.uncertainty_geometry, "properties": {**common, "layer": "uncertainty_polygon"}}
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/risk-zones")
def map_risk_zones(db: Session = Depends(get_db)) -> dict:
    """Uncertainty polygons for HIGH/CRITICAL risk detections only, for a focused risk overlay."""
    from app.models.other import RiskAssessment

    features = []
    high_risk_ids = {
        r.detection_id
        for r in db.query(RiskAssessment).filter(RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"])).all()
    }
    if not high_risk_ids:
        return {"type": "FeatureCollection", "features": []}

    trajectories = db.query(Trajectory).filter(Trajectory.detection_id.in_(high_risk_ids)).all()
    detections_by_id = {d.id: d for d in db.query(Detection).filter(Detection.id.in_(high_risk_ids)).all()}
    risk_by_detection = {
        r.detection_id: r
        for r in db.query(RiskAssessment).filter(RiskAssessment.detection_id.in_(high_risk_ids)).all()
    }

    for t in trajectories:
        detection = detections_by_id.get(t.detection_id)
        risk = risk_by_detection.get(t.detection_id)
        if detection is None or risk is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": t.uncertainty_geometry,
                "properties": {
                    "detection_id": detection.external_id,
                    "forecast_hour": t.forecast_hour,
                    "risk_level": risk.risk_level,
                    "risk_score": risk.risk_score,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/protected-areas")
def map_protected_areas() -> dict:
    return load_protected_areas()


@router.get("/habitats")
def map_habitats() -> dict:
    return load_habitats()


@router.get("/layers")
def map_layers() -> dict:
    """List every available map layer, its endpoint, and its data source label."""
    return {
        "layers": [
            {"id": "detections", "endpoint": "/api/v1/map/detections", "source": "GhostNet database"},
            {"id": "trajectories", "endpoint": "/api/v1/map/trajectories", "source": "GhostNet drift engine"},
            {"id": "risk_zones", "endpoint": "/api/v1/map/risk-zones", "source": "GhostNet risk engine"},
            {
                "id": "protected_areas",
                "endpoint": "/api/v1/map/protected-areas",
                "source": load_protected_areas()["properties"]["source_name"],
                "license": load_protected_areas()["properties"]["license"],
            },
            {
                "id": "habitats",
                "endpoint": "/api/v1/map/habitats",
                "source": load_habitats()["properties"]["source_name"],
                "license": load_habitats()["properties"]["license"],
            },
            {
                "id": "coastline",
                "source": load_coastline()["properties"]["source_name"],
                "license": load_coastline()["properties"]["license"],
            },
            {
                "id": "coral_reefs",
                "endpoint": "/api/v1/map/coral-reefs",
                "source": "UNEP-WCMC Global Coral Reef Monitoring Network (GCRMN)",
                "license": "CC-BY 4.0",
            },
            {
                "id": "species_habitats",
                "endpoint": "/api/v1/map/species-habitats",
                "source": "OBIS Ocean Biodiversity Information System / IUCN Red List",
                "license": "CC-BY 4.0 (OBIS)",
            },
            {
                "id": "ecological_alerts",
                "endpoint": "/api/v1/alerts/map/geojson",
                "source": "OceanGuard Ecological Alert Engine",
            },
            {
                "id": "ocean_currents",
                "endpoint": "/api/v1/map/currents",
                "source": "Copernicus Marine Service (CMEMS) - Global Ocean Physics Analysis and Forecast",
                "license": "E.U. Copernicus Marine Service (Open Access)",
            },
        ]
    }


@router.get("/currents")
def map_currents(force_refresh: bool = False) -> dict:
    """Real-time ocean surface current flow vectors from Copernicus Marine Service (CMEMS)."""
    from app.drift.currents_service import fetch_cmems_ocean_currents
    return fetch_cmems_ocean_currents(force_refresh=force_refresh)


@router.get("/coral-reefs")
def map_coral_reefs() -> dict:
    """GeoJSON FeatureCollection of coral reef zones from GCRMN/UNEP-WCMC."""
    from app.geospatial.data_collector import get_coral_reefs
    return get_coral_reefs()


@router.get("/species-habitats")
def map_species_habitats() -> dict:
    """GeoJSON FeatureCollection of turtle, whale, dolphin, dugong, and shark habitats."""
    from app.geospatial.data_collector import get_species_habitats
    return get_species_habitats()


@router.get("/extended-mpas")
def map_extended_mpas() -> dict:
    """GeoJSON FeatureCollection of extended MPA data from WDPA/ProtectedPlanet."""
    from app.geospatial.data_collector import get_extended_mpas
    return get_extended_mpas()

