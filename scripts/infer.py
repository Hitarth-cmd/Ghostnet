#!/usr/bin/env python3
"""
Run the real Sentinel-2 detection model on a single GeoTIFF scene and save
the resulting detections to the database.

Requires MODEL_PROVIDER=sentinel2 and MODEL_CHECKPOINT_PATH set to your
trained checkpoint (see README "Model integration" / "Batch inference").
Without a checkpoint installed, this will fail with a clear
ModelNotConfiguredError rather than fabricating detections.

Usage:
    python scripts/infer.py --image scene.tif
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal, init_db  # noqa: E402
from app.detection.providers.model import Sentinel2ModelProvider  # noqa: E402
from app.models.detection import Detection  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sentinel-2 model inference on a GeoTIFF")
    parser.add_argument("--image", required=True, help="Path to a Sentinel-2 GeoTIFF scene")
    parser.add_argument("--checkpoint", default=None, help="Override MODEL_CHECKPOINT_PATH")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    provider = Sentinel2ModelProvider(checkpoint_path=args.checkpoint)
    records = provider.run_on_geotiff(args.image)

    init_db()
    db = SessionLocal()
    try:
        for record in records:
            db.add(
                Detection(
                    external_id=record.external_id,
                    latitude=record.latitude,
                    longitude=record.longitude,
                    geometry=record.geometry,
                    confidence=record.confidence,
                    object_class=record.object_class.value,
                    status=record.status.value,
                    timestamp=record.timestamp,
                    source=record.source,
                    scene_id=record.scene_id,
                    area_m2=record.area_m2,
                )
            )
        db.commit()
    finally:
        db.close()

    print(f"Created {len(records)} detections from {args.image}")


if __name__ == "__main__":
    main()
