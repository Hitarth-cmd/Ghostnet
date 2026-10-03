#!/usr/bin/env python3
"""
Runs the complete GhostNet pipeline programmatically with zero external
services: seeds the deterministic demo detections, then runs the full
analysis pipeline (drift -> geospatial -> risk -> priority -> RAG ->
report) for every demo detection.

Usage:
    python scripts/demo.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal, init_db  # noqa: E402
from app.orchestrator.pipeline import analyze_detection  # noqa: E402
from app.seed import seed_demo_data  # noqa: E402


def main() -> int:
    print("DEMO START")

    init_db()
    db = SessionLocal()
    try:
        created = seed_demo_data(db)
        print(f"Detection loaded ({created} new, demo catalogue ready)")

        from app.models.detection import Detection

        detection_ids = [d.external_id for d in db.query(Detection).order_by(Detection.external_id).all()]

        for external_id in detection_ids:
            result = analyze_detection(db, external_id)

            horizons_done = sorted(h.forecast_hour for h in result.drift.horizons)
            for h in horizons_done:
                print(f"{h}h trajectory generated ({external_id})")

            print(f"Spatial analysis completed ({external_id})")
            print(f"Risk calculated ({external_id}): {result.risk['risk_level']} ({result.risk['risk_score']})")
            print(f"Priority calculated ({external_id}): {result.priority['priority_level']}")
            print(f"RAG completed ({external_id}): {len(result.report.evidence)} evidence chunks")
            print(f"Report generated ({external_id})")

        print("DEMO SUCCESS")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
