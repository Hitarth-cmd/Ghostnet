from __future__ import annotations

import argparse
import json
import sys

from app.database import SessionLocal, init_db
from app.models.detection import Detection
from app.orchestrator.pipeline import DetectionNotFoundError, analyze_detection
from app.seed import seed_demo_data


def cmd_seed_demo(_args: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        created = seed_demo_data(db)
        print(f"Seeded demo data. New detections created: {created}")
    finally:
        db.close()


def cmd_list_detections(_args: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        detections = db.query(Detection).order_by(Detection.external_id).all()
        for d in detections:
            print(f"{d.external_id}  {d.object_class:28s}  {d.status:12s}  conf={d.confidence:.2f}  "
                  f"({d.latitude:.4f}, {d.longitude:.4f})")
        print(f"\nTotal: {len(detections)}")
    finally:
        db.close()


def cmd_run_analysis(args: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)  # ensure the referenced demo detection exists
        try:
            result = analyze_detection(db, args.detection_id)
        except DetectionNotFoundError:
            print(f"ERROR: detection '{args.detection_id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result.model_dump(mode="json"), indent=2))
    finally:
        db.close()


def cmd_health(_args: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        print("healthy")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="GhostNet CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-demo", help="Load deterministic demo detections into the database")
    subparsers.add_parser("list-detections", help="List all detections in the database")
    subparsers.add_parser("health", help="Check database connectivity")

    run_analysis_parser = subparsers.add_parser("run-analysis", help="Run the full analysis pipeline for a detection")
    run_analysis_parser.add_argument("detection_id", help="External detection id, e.g. DEMO-001")

    args = parser.parse_args()
    commands = {
        "seed-demo": cmd_seed_demo,
        "list-detections": cmd_list_detections,
        "run-analysis": cmd_run_analysis,
        "health": cmd_health,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
