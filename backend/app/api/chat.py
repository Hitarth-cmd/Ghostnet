"""FastAPI router for the vessel chatbot endpoint.

POST /api/v1/chat
  → Intent extraction → Geocoding → Corridor geometry
  → Debris DB query → Reply generation → GeoJSON overlay response
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.chat.debris_query import hotspots_to_geojson_features, query_debris_in_corridor
from app.chat.geocoder import geocode
from app.chat.geometry_utils import (
    build_corridor,
    corridor_to_geojson_feature,
    destination_point,
    route_to_geojson_feature,
)
from app.chat.intent_parser import get_intent_parser
from app.chat.reply_generator import get_reply_generator
from app.chat.schemas import ChatRequest, ChatResponse, OriginCoords, ParsedQuery
from app.chat.session_store import (
    add_message,
    get_last_parsed_query,
    store_parsed_query,
)
from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger("ghostnet.chat.api")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=ChatResponse, summary="Vessel debris route query chatbot")
def chat(request: ChatRequest, db: Session = Depends(_get_db)) -> ChatResponse:
    """Natural-language chatbot for vessel owners.

    Extracts route parameters from the message, builds a corridor polygon,
    queries the detection database, and returns a friendly reply plus a
    GeoJSON overlay for the map.
    """
    settings = get_settings()
    session_id = request.session_id

    # ── 1. Retrieve session context for multi-turn ────────────────────────
    last_query = get_last_parsed_query(session_id)
    ctx = last_query.model_dump() if last_query else {}

    # ── 2. Intent extraction ──────────────────────────────────────────────
    parser = get_intent_parser(
        llm_provider=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
    )
    add_message(session_id, "user", request.message)

    try:
        parsed = parser.parse(request.message, session_context=ctx)
    except Exception as exc:
        logger.error("Intent parser raised: %s", exc)
        raise HTTPException(status_code=500, detail=f"Intent parsing failed: {exc}") from exc

    # ── 3. Off-topic guard ────────────────────────────────────────────────
    if parsed.intent == "off_topic":
        reply_gen = get_reply_generator(settings.LLM_PROVIDER, settings.LLM_API_KEY, settings.LLM_MODEL)
        reply = reply_gen.generate(parsed, None)
        add_message(session_id, "assistant", reply)
        return ChatResponse(
            reply=reply,
            parsed_query=parsed,
            needs_clarification=False,
            session_id=session_id,
        )

    # ── 4. Clarification check ────────────────────────────────────────────
    if parsed.needs_clarification:
        reply_gen = get_reply_generator(settings.LLM_PROVIDER, settings.LLM_API_KEY, settings.LLM_MODEL)
        reply = reply_gen.generate(parsed, None)
        add_message(session_id, "assistant", reply)
        return ChatResponse(
            reply=reply,
            parsed_query=parsed,
            needs_clarification=True,
            session_id=session_id,
        )

    # ── 5. Geocode origin ─────────────────────────────────────────────────
    # If the user gave their GPS location and mentioned "near me", use that
    origin_name = parsed.origin_name or "user location"
    try:
        if (
            parsed.origin_name is None
            and request.user_location is not None
        ):
            origin_lat = request.user_location.lat
            origin_lon = request.user_location.lon
            origin_name = "your current location"
        elif parsed.origin_name:
            origin_lat, origin_lon = geocode(parsed.origin_name)
        else:
            raise ValueError("No origin name or GPS location provided.")
    except ValueError as exc:
        reply = (
            f"I couldn't find '{parsed.origin_name}' on the map. "
            "Please try a major Gujarat port name like 'Mundra', 'Kandla', or 'Okha'."
        )
        add_message(session_id, "assistant", reply)
        return ChatResponse(
            reply=reply,
            parsed_query=parsed,
            needs_clarification=True,
            session_id=session_id,
        )

    parsed = parsed.model_copy(
        update={"origin_coords": OriginCoords(lat=origin_lat, lon=origin_lon)}
    )

    # ── 6. Build corridor geometry ────────────────────────────────────────
    bearing = parsed.bearing_deg if parsed.bearing_deg is not None else 270.0  # default west
    distance_km = parsed.distance_km or 30.0
    radius_km = parsed.search_radius_km

    dest_lat, dest_lon = destination_point(origin_lat, origin_lon, bearing, distance_km)
    corridor = build_corridor(origin_lat, origin_lon, dest_lat, dest_lon, radius_km)

    # ── 7. Query debris database ──────────────────────────────────────────
    try:
        summary = query_debris_in_corridor(
            db=db,
            corridor_polygon=corridor,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            date_iso=parsed.date,
        )
    except Exception as exc:
        logger.error("Debris query failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Debris query failed: {exc}") from exc

    # ── 8. Build GeoJSON overlay ──────────────────────────────────────────
    route_meta = {
        "origin_name": origin_name,
        "bearing_deg": bearing,
        "distance_km": distance_km,
        "date": parsed.date,
    }
    features = [
        route_to_geojson_feature(origin_lat, origin_lon, dest_lat, dest_lon, route_meta),
        corridor_to_geojson_feature(corridor, {"search_radius_km": radius_km}),
        *hotspots_to_geojson_features(summary.hotspots),
    ]
    geojson = {"type": "FeatureCollection", "features": features}

    # ── 9. Generate natural-language reply ────────────────────────────────
    reply_gen = get_reply_generator(settings.LLM_PROVIDER, settings.LLM_API_KEY, settings.LLM_MODEL)
    reply = reply_gen.generate(parsed, summary)

    # ── 10. Persist to session ────────────────────────────────────────────
    store_parsed_query(session_id, parsed)
    add_message(session_id, "assistant", reply)

    return ChatResponse(
        reply=reply,
        parsed_query=parsed,
        geojson=geojson,
        summary=summary,
        needs_clarification=False,
        session_id=session_id,
    )
