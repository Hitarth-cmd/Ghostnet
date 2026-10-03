from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import PriorityLevel


class PriorityOut(BaseModel):
    detection_id: str
    priority_rank: int
    priority_level: PriorityLevel
    recommended_action: str
    contributing_factors: list[str]
