from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.detection.providers.base import DetectionProvider
from app.detection.providers.mock import MockDetectionProvider
from app.detection.providers.model import Sentinel2ModelProvider


@lru_cache
def get_detection_provider() -> DetectionProvider:
    settings = get_settings()
    if settings.MODEL_PROVIDER == "sentinel2":
        return Sentinel2ModelProvider()
    return MockDetectionProvider()
