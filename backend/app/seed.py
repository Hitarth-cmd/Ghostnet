from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.detection.providers.mock import MockDetectionProvider
from app.models.detection import Detection
from app.models.other import DataSource, Report
from app.models.user import IncidentAction, User

logger = logging.getLogger("ghostnet.seed")


def seed_demo_data(db: Session) -> int:
    """Idempotently ingest Sentinel-2 data from Earth Engine (balmy-ocean-509105-v8),
    run marine debris AI model inference, seed responder accounts, and analyze incidents."""
    from app.detection.earthengine_scanner import ingest_and_scan_all_regions

    # 1. Ingest Sentinel-2 from Earth Engine and run ViT-UNet++ AI segmentation
    created = ingest_and_scan_all_regions(db, force=True)

    # 2. Seed demo users (NGOs, Responders, Researchers, Admins)
    demo_users = [
        {
            "email": "responder@oceanguard.org",
            "password": "responder123",
            "full_name": "Dr. Anya Sharma",
            "organization": "Ocean Guardians Marine NGO",
            "role": "responder",
            "phone": "+91-98765-43210",
        },
        {
            "email": "cleanup@marinerescue.org",
            "password": "cleanup123",
            "full_name": "Captain Vikram Rao",
            "organization": "Rapid Marine Cleanup Taskforce",
            "role": "responder",
            "phone": "+91-98111-22334",
        },
        {
            "email": "researcher@incois.gov.in",
            "password": "researcher123",
            "full_name": "Priya Nair",
            "organization": "INCOIS Ocean Observation",
            "role": "researcher",
            "phone": "+91-98222-33445",
        },
        {
            "email": "admin@oceanguard.org",
            "password": "admin123456",
            "full_name": "Systems Director",
            "organization": "OceanGuard AI Command",
            "role": "admin",
            "phone": "+91-98333-44556",
        },
    ]

    for u_data in demo_users:
        existing_user = db.query(User).filter(User.email == u_data["email"]).one_or_none()
        if existing_user is None:
            user = User(
                email=u_data["email"],
                hashed_password=hash_password(u_data["password"]),
                full_name=u_data["full_name"],
                organization=u_data["organization"],
                role=u_data["role"],
                phone=u_data["phone"],
                is_active=True,
            )
            db.add(user)
    db.commit()

    # 3. Run multi-agent pipeline on any detections without analysis reports
    from app.orchestrator.pipeline import analyze_detection

    all_detections = db.query(Detection).all()
    for det in all_detections:
        existing_report = db.query(Report).filter(Report.detection_id == det.id).first()
        if existing_report is None:
            try:
                analyze_detection(db, det.external_id)
                logger.info("[SEED] Analyzed detection %s", det.external_id)
            except Exception as e:
                logger.warning("[SEED] Could not auto-analyze %s: %s", det.external_id, e)

    # 4. Set realistic incident states for demo showcase
    # Make DEMO-001 "assigned" to Captain Vikram Rao
    det_001 = db.query(Detection).filter(Detection.external_id == "DEMO-001").first()
    if det_001 and (det_001.incident_status in (None, "unverified", "verified")):
        det_001.incident_status = "assigned"
        det_001.status = "assigned"
        det_001.assigned_team = "Rapid Marine Cleanup Taskforce"
        det_001.assigned_to = "Captain Vikram Rao"
        det_001.verified_by = "Dr. Anya Sharma"
        det_001.verified_at = dt.datetime.utcnow() - dt.timedelta(hours=4)
        det_001.verification_notes = "Verified debris field approaching Malvan Marine Sanctuary. Interception vessel dispatched."
        db.add(
            IncidentAction(
                detection_id=det_001.id,
                user_name="Dr. Anya Sharma",
                organization="Ocean Guardians Marine NGO",
                action="verify",
                previous_status="unverified",
                new_status="verified",
                notes="Confirmed net cluster on satellite SAR.",
                created_at=dt.datetime.utcnow() - dt.timedelta(hours=4),
            )
        )
        db.add(
            IncidentAction(
                detection_id=det_001.id,
                user_name="Captain Vikram Rao",
                organization="Rapid Marine Cleanup Taskforce",
                action="assign",
                previous_status="verified",
                new_status="assigned",
                assigned_team="Vessel Sagar Rakshak-2",
                notes="En route to intercept before sanctuary perimeter.",
                created_at=dt.datetime.utcnow() - dt.timedelta(hours=2),
            )
        )

    # Make DEMO-002 "being_handled"
    det_002 = db.query(Detection).filter(Detection.external_id == "DEMO-002").first()
    if det_002 and (det_002.incident_status in (None, "unverified", "verified")):
        det_002.incident_status = "being_handled"
        det_002.status = "being_handled"
        det_002.assigned_team = "Coastal Response Unit Goa"
        det_002.assigned_to = "Dr. Anya Sharma"
        det_002.verified_by = "Dr. Anya Sharma"
        det_002.verified_at = dt.datetime.utcnow() - dt.timedelta(hours=6)
        det_002.verification_notes = "Cleanup vessel currently deploying boom and retrieval crane."
        db.add(
            IncidentAction(
                detection_id=det_002.id,
                user_name="Dr. Anya Sharma",
                organization="Ocean Guardians Marine NGO",
                action="being_handled",
                previous_status="assigned",
                new_status="being_handled",
                assigned_team="Coastal Response Unit Goa",
                notes="Recovery operation active. Retrieval net deployed.",
                created_at=dt.datetime.utcnow() - dt.timedelta(hours=1),
            )
        )

    # Ensure all other detections have incident_status initialized if None
    for d in db.query(Detection).filter(Detection.incident_status.is_(None)).all():
        d.incident_status = d.status or "unverified"

    # 5. Data sources provenance
    if db.query(DataSource).count() == 0:
        db.add_all(
            [
                DataSource(
                    name="GhostNet Demo Detections",
                    category="detections",
                    license="Sentinel-2 / SAR / Mock",
                    dataset_version="demo-1.0",
                    is_demo=True,
                ),
                DataSource(
                    name="UNEP-WCMC Protected Planet (WDPA)",
                    category="protected_areas",
                    license="CC BY 3.0 IGO",
                    dataset_version="wdpa-2024",
                    is_demo=False,
                ),
                DataSource(
                    name="UNEP-WCMC Global Distribution of Coral Reefs (WCMC 008)",
                    category="coral_reefs",
                    license="WCMC Data Licence / CC BY 4.0",
                    dataset_version="v4.1",
                    is_demo=False,
                ),
                DataSource(
                    name="State of the World's Sea Turtles (SWOT) / OBIS-SEAMAP",
                    category="habitats",
                    license="OBIS Open Access / IUCN MTSG",
                    dataset_version="swot-2024",
                    is_demo=False,
                ),
                DataSource(
                    name="NOAA Global Self-consistent Hierarchical High-resolution Geography (GSHHG)",
                    category="coastline",
                    license="Public Domain / LGPL",
                    dataset_version="2.3.7",
                    is_demo=False,
                ),
            ]
        )

    db.commit()
    logger.info("[DATABASE] seed complete - %d new detections, demo users and alerts seeded", created)
    return created
