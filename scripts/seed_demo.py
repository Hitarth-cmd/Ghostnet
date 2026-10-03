#!/usr/bin/env python3
"""Idempotently seed the deterministic demo detections and dataset provenance.

Usage:
    python scripts/seed_demo.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal, init_db  # noqa: E402
from app.seed import seed_demo_data  # noqa: E402


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        created = seed_demo_data(db)
        print(f"Seed complete. New detections created: {created}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
