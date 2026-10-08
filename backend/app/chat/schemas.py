"""Pydantic schemas for the vessel chatbot pipeline."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class UserLocation(BaseModel):
    lat: float
    lon: float


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="anonymous", max_length=128)
    user_location: UserLocation | None = None


class OriginCoords(BaseModel):
    lat: float
    lon: float


class ParsedQuery(BaseModel):
    intent: Literal["debris_near_route", "off_topic", "clarification_needed"] = "debris_near_route"
    date: str | None = None                # ISO-8601 date string, e.g. "2026-10-09"
    date_label: str | None = None          # Human-readable, e.g. "tomorrow"
    origin_name: str | None = None
    origin_coords: OriginCoords | None = None
    bearing_deg: float | None = None       # 0=N, 90=E, 180=S, 270=W
    bearing_label: str | None = None       # "west", "southwest", etc.
    distance_km: float | None = None
    search_radius_km: float = 5.0
    needs_clarification: bool = False
    clarification_field: str | None = None  # Which field needs clarification
    raw_message: str = ""


class HotspotPoint(BaseModel):
    lat: float
    lon: float
    object_class: str
    count: int
    confidence_avg: float
    distance_from_start_km: float


class DebrisSummary(BaseModel):
    total_debris: int
    ghost_nets: int
    suspected_ghost_gear: int
    other_debris: int
    unknown_objects: int
    hotspots: list[HotspotPoint]
    data_date: str | None
    nearest_available_date: str | None
    data_source: str = "OceanGuard Detection Database"


class ChatResponse(BaseModel):
    reply: str
    parsed_query: ParsedQuery
    geojson: dict[str, Any] | None = None   # FeatureCollection or None
    summary: DebrisSummary | None = None
    needs_clarification: bool = False
    session_id: str = "anonymous"
