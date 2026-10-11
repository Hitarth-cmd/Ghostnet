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

    # 1. Ingest Sentinel-2 from Earth Engine and run ViT-UNet++ AI segmentation across all regions
    created = ingest_and_scan_all_regions(db, force=True)

    # 2. Seed Pelagic Indian Ocean marine debris targets across open oceanic basins
    pelagic_targets = [
        ("IO-PELAGIC-001", "Central Arabian Sea Drift Gyre", 14.85, 69.40, 0.88, "suspected_ghost_gear", "unverified", 420.0),
        ("IO-PELAGIC-002", "Northern Arabian Sea Deep Basin", 19.50, 66.80, 0.76, "marine_debris", "verified", 185.0),
        ("IO-PELAGIC-003", "Somalia Basin Entry Corridor", 9.20, 68.10, 0.84, "suspected_ghost_gear", "unverified", 540.0),
        ("IO-PELAGIC-004", "Wadge Bank Outer Shelf", 7.15, 77.20, 0.92, "suspected_ghost_gear", "assigned", 310.0),
        ("IO-PELAGIC-005", "South Sri Lanka Maritime Highway", 5.60, 80.50, 0.89, "marine_debris", "being_handled", 890.0),
        ("IO-PELAGIC-006", "Hambantota Deep Oceanic Fairway", 5.75, 81.65, 0.74, "unknown_floating_object", "unverified", 140.0),
        ("IO-PELAGIC-007", "Mid Bay of Bengal Cyclonic Drift", 15.60, 86.80, 0.82, "marine_debris", "verified", 260.0),
        ("IO-PELAGIC-008", "Northern Bay of Bengal Deepwater", 18.90, 88.50, 0.79, "suspected_ghost_gear", "unverified", 380.0),
        ("IO-PELAGIC-009", "Palk Bay Outer Shoals", 9.85, 79.80, 0.91, "suspected_ghost_gear", "assigned", 620.0),
        ("IO-PELAGIC-010", "Point Calimere Coastal Confluence", 10.45, 80.20, 0.83, "marine_debris", "verified", 195.0),
        ("IO-PELAGIC-011", "Puducherry Continental Shelf", 11.95, 80.20, 0.77, "marine_debris", "resolved", 150.0),
        ("IO-PELAGIC-012", "Nellore Upwelling Corridor", 14.45, 80.50, 0.86, "suspected_ghost_gear", "unverified", 440.0),
        ("IO-PELAGIC-013", "Rushikulya Turtle Corridor", 19.10, 85.40, 0.95, "suspected_ghost_gear", "being_handled", 710.0),
        ("IO-PELAGIC-014", "Paradip Outer Anchorage", 20.15, 86.95, 0.81, "marine_debris", "verified", 230.0),
        ("IO-PELAGIC-015", "Little Andaman Oceanic Trench", 10.40, 92.65, 0.87, "suspected_ghost_gear", "unverified", 580.0),
        ("IO-PELAGIC-016", "Havelock Island Outer Reef", 12.15, 93.25, 0.93, "suspected_ghost_gear", "assigned", 490.0),
        ("IO-PELAGIC-017", "Maldives Central Atoll Channel", 4.10, 73.40, 0.78, "marine_debris", "resolved", 165.0),
        ("IO-PELAGIC-018", "Equatorial Current Convergence", 3.20, 82.50, 0.85, "suspected_ghost_gear", "unverified", 820.0),
    ]

    now = dt.datetime.utcnow()
    for ext_id, name, lat, lon, conf, o_class, status, area in pelagic_targets:
        existing_pelagic = db.query(Detection).filter(Detection.external_id == ext_id).one_or_none()
        delta = 0.012
        poly = [
            [
                [round(lon - delta, 5), round(lat - delta, 5)],
                [round(lon + delta, 5), round(lat - delta, 5)],
                [round(lon + delta, 5), round(lat + delta, 5)],
                [round(lon - delta, 5), round(lat + delta, 5)],
                [round(lon - delta, 5), round(lat - delta, 5)],
            ]
        ]
        if existing_pelagic is None:
            p_det = Detection(
                external_id=ext_id,
                latitude=lat,
                longitude=lon,
                confidence=conf,
                object_class=o_class,
                status=status,
                incident_status=status,
                timestamp=now - dt.timedelta(hours=int(lon) % 48),
                source="Sentinel-2 Multispectral & SAR",
                scene_id=f"S2-INDIAN-OCEAN-{ext_id}",
                area_m2=area,
                geometry={"type": "Polygon", "coordinates": poly},
            )
            db.add(p_det)
            created += 1
        else:
            existing_pelagic.latitude = lat
            existing_pelagic.longitude = lon
            existing_pelagic.confidence = conf
            existing_pelagic.incident_status = status
            existing_pelagic.status = status
            existing_pelagic.geometry = {"type": "Polygon", "coordinates": poly}
    db.commit()

    # 3. Seed demo users (NGO and Admin)
    demo_users = [
        {
            "email": "responder@oceanguard.org",
            "password": "responder123",
            "full_name": "Dr. Anya Sharma",
            "organization": "Ocean Guardians Marine NGO",
            "role": "ngo",
            "phone": "+91-98765-43210",
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

    # 4. Set realistic incident states for demo showcase
    # Make S2-GEE-001 (Goa) "assigned" to Captain Vikram Rao
    det_001 = db.query(Detection).filter(Detection.external_id == "S2-GEE-001").first()
    if det_001:
        det_001.incident_status = "assigned"
        det_001.status = "assigned"
        det_001.assigned_team = "Rapid Marine Cleanup Taskforce"
        det_001.assigned_to = "Captain Vikram Rao"
        det_001.verified_by = "Dr. Anya Sharma"
        det_001.verified_at = dt.datetime.utcnow() - dt.timedelta(hours=4)
        det_001.verification_notes = "Verified debris field approaching Mandovi plume. Interception vessel dispatched."
        db.add(
            IncidentAction(
                detection_id=det_001.id,
                user_name="Dr. Anya Sharma",
                organization="Ocean Guardians Marine NGO",
                action="verify",
                previous_status="unverified",
                new_status="verified",
                notes="Confirmed net cluster on Sentinel-2 satellite inference.",
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

    # Make S2-GEE-002 (Mumbai) "being_handled"
    det_002 = db.query(Detection).filter(Detection.external_id == "S2-GEE-002").first()
    if det_002:
        det_002.incident_status = "being_handled"
        det_002.status = "being_handled"
        det_002.assigned_team = "Coastal Response Unit Mumbai"
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
                assigned_team="Coastal Response Unit Mumbai",
                notes="Recovery operation active. Retrieval net deployed in Mumbai fairway.",
                created_at=dt.datetime.utcnow() - dt.timedelta(hours=1),
            )
        )

    # Make S2-GEE-003 (Gulf of Mannar) "verified"
    det_003 = db.query(Detection).filter(Detection.external_id == "S2-GEE-003").first()
    if det_003:
        det_003.incident_status = "verified"
        det_003.status = "verified"
        det_003.verified_by = "Dr. Anya Sharma"
        det_003.verified_at = dt.datetime.utcnow() - dt.timedelta(hours=3)
        det_003.verification_notes = "High-risk ghost gear detected 4.2 km from coral reef barrier."

    # Make S2-GEE-005 (Kochi) "resolved"
    det_005 = db.query(Detection).filter(Detection.external_id == "S2-GEE-005").first()
    if det_005:
        det_005.incident_status = "resolved"
        det_005.status = "resolved"
        det_005.assigned_team = "Kerala Fisheries Response"
        det_005.assigned_to = "Officer Rajan Pillai"
        det_005.verification_notes = "380 kg discarded monofilament nylon net retrieved successfully."

    # 5. Run multi-agent pipeline on any detections without analysis reports
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

    # Ensure all detections have incident_status initialized if None
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
