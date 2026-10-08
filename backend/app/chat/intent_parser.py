"""Intent parser: extracts structured parameters from a free-text vessel message.

Strategy
--------
1. Rule-based / regex parser (MockIntentParser) — works with zero LLM key,
   deterministic, fast, covers the primary use-cases.
2. LLMIntentParser — uses the existing LLM_PROVIDER setting when configured;
   the LLM ONLY extracts a JSON schema, it never invents debris numbers.

The extracted ParsedQuery is validated by Pydantic; any missing field
sets `needs_clarification=True` with the first missing `clarification_field`.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from abc import ABC, abstractmethod

from app.chat.geometry_utils import cardinal_to_bearing, bearing_label
from app.chat.schemas import ParsedQuery

logger = logging.getLogger("ghostnet.chat.intent_parser")

# ─── Date resolution ─────────────────────────────────────────────────────────

_WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _resolve_date(text: str, today: dt.date | None = None) -> tuple[str | None, str | None]:
    """Return (iso_date_str, human_label) or (None, None) if not found."""
    today = today or dt.date.today()
    t = text.lower()

    if "day after tomorrow" in t:
        return (today + dt.timedelta(days=2)).isoformat(), "day after tomorrow"
    if "today" in t:
        return today.isoformat(), "today"
    if "tomorrow" in t or "tmrw" in t or "tmr" in t:
        return (today + dt.timedelta(days=1)).isoformat(), "tomorrow"
    if "this weekend" in t:
        days_to_sat = (5 - today.weekday()) % 7
        return (today + dt.timedelta(days=days_to_sat)).isoformat(), "this weekend"
    if "next week" in t:
        return (today + dt.timedelta(days=7)).isoformat(), "next week"

    # Weekday name ("this friday", "on thursday")
    for day_name, day_num in _WEEKDAY_MAP.items():
        if day_name in t:
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # next occurrence
            target = today + dt.timedelta(days=days_ahead)
            return target.isoformat(), day_name.capitalize()

    # Ordinal / numeric patterns: "9th", "Oct 9", "9 October", "09/10"
    patterns = [
        (r"\b(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b", "%d %b"),
        (r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})\b", None),
    ]
    for pat, _ in patterns:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            try:
                raw = m.group(0)
                for fmt in ("%d %b", "%d %B", "%b %d", "%B %d"):
                    try:
                        d = dt.datetime.strptime(raw, fmt)
                        target = d.replace(year=today.year).date()
                        if target < today:
                            target = target.replace(year=today.year + 1)
                        return target.isoformat(), raw
                    except ValueError:
                        pass
            except Exception:
                pass

    return None, None


# ─── Distance resolution ─────────────────────────────────────────────────────

def _resolve_distance(text: str) -> float | None:
    """Extract distance in km from text."""
    # "40 km", "40km", "40 kilometers", "25 nautical miles", "25 nm", "25 nmi"
    nm = re.search(r"(\d+(?:\.\d+)?)\s*(?:nautical\s*miles?|nmi|nm)\b", text, re.IGNORECASE)
    if nm:
        return round(float(nm.group(1)) * 1.852, 1)

    km = re.search(r"(\d+(?:\.\d+)?)\s*(?:km|kms|kilometers?|kilometres?)\b", text, re.IGNORECASE)
    if km:
        return float(km.group(1))

    mi = re.search(r"(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b", text, re.IGNORECASE)
    if mi:
        return round(float(mi.group(1)) * 1.60934, 1)

    # bare number followed by nothing specific — treat as km if < 500
    bare = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    if bare:
        val = float(bare.group(1))
        if 0.5 < val < 500:
            return val
    return None


# ─── Direction resolution ────────────────────────────────────────────────────

def _resolve_bearing(text: str) -> tuple[float | None, str | None]:
    """Return (bearing_deg, label) from text."""
    t = text.lower()

    # Numeric degree: "bearing 270", "270°", "heading 270"
    m = re.search(r"(?:bearing|heading|course)\s*(\d+(?:\.\d+)?)\s*°?", t)
    if m:
        deg = float(m.group(1)) % 360
        return deg, bearing_label(deg)

    # Try whole-word cardinal directions (longer first)
    for label in ["north-west", "north-east", "south-west", "south-east",
                  "northwest", "northeast", "southwest", "southeast",
                  "north", "south", "east", "west",
                  "nw", "ne", "sw", "se",
                  "n", "s", "e", "w"]:
        if re.search(rf"\b{re.escape(label)}\b", t):
            deg = cardinal_to_bearing(label)
            if deg is not None:
                return deg, bearing_label(deg)

    return None, None


# ─── Origin extraction ───────────────────────────────────────────────────────

_ORIGIN_PATTERNS = [
    r"(?:from|leaving|departing?|starting?\s+(?:from|at)|out\s+of)\s+([A-Za-z][A-Za-z\s']{2,40}?)(?:\s+(?:and|heading|going|toward|towards|to\b|tomorrow|today|tmrw|tmr|for\b|,|\.|$))",
    r"(?:from|leaving|departing?)\s+([A-Za-z][A-Za-z\s']{2,40}?)(?:\s*$)",
    r"(?:near|around|close\s+to|off(?:\s+the\s+coast\s+of)?)\s+([A-Za-z][A-Za-z\s']{2,40}?)(?:\s+(?:and|heading|going|toward|towards|,|\.|$))",
]


def _extract_origin(text: str) -> str | None:
    for pat in _ORIGIN_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().rstrip(",.")
            candidate = re.sub(r"^(?:from\s+(?:the\s+)?|out\s+of\s+(?:the\s+)?|the\s+)", "", candidate, flags=re.IGNORECASE).strip()
            if len(candidate) > 2:
                return candidate
    return None


# ─── Search radius ───────────────────────────────────────────────────────────

def _resolve_radius(text: str) -> float:
    """Extract an explicit corridor radius from text, default 5 km."""
    m = re.search(
        r"(?:within|radius|buffer|corridor)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:km|kilometers?|nautical\s*miles?|nmi|nm)?",
        text, re.IGNORECASE,
    )
    if m:
        val = float(m.group(1))
        if "naut" in m.group(0).lower() or "nm" in m.group(0).lower():
            val *= 1.852
        return min(max(val, 1.0), 50.0)
    return 5.0


# ─── Off-topic detection ─────────────────────────────────────────────────────

_OFF_TOPIC_SIGNALS = [
    "weather forecast", "stock price", "cricket", "recipe",
    "translate", "who is", "capital of", "population of",
    "covid", "politics", "religion", "joke",
]


def _is_off_topic(text: str) -> bool:
    t = text.lower()
    debris_keywords = [
        "debris", "ghost net", "fishing net", "net", "plastic",
        "marine", "ocean", "sea", "route", "vessel", "boat",
        "ship", "collect", "heading", "going", "leaving", "km", "nautical",
        "direction", "north", "south", "east", "west", "debris",
    ]
    has_debris = any(kw in t for kw in debris_keywords)
    has_off = any(kw in t for kw in _OFF_TOPIC_SIGNALS)
    return has_off or not has_debris


# ─── Abstract base + Mock implementation ─────────────────────────────────────

class BaseIntentParser(ABC):
    @abstractmethod
    def parse(self, message: str, session_context: dict | None = None) -> ParsedQuery:
        """Parse *message* → ParsedQuery (raises on hard error)."""


class MockIntentParser(BaseIntentParser):
    """Regex-rule-based parser. Zero dependencies, fully deterministic."""

    def parse(self, message: str, session_context: dict | None = None) -> ParsedQuery:
        ctx = session_context or {}

        has_off = any(kw in message.lower() for kw in _OFF_TOPIC_SIGNALS)
        if has_off:
            return ParsedQuery(intent="off_topic", raw_message=message)

        if not ctx and _is_off_topic(message):
            return ParsedQuery(intent="off_topic", raw_message=message)

        date_iso, date_label = _resolve_date(message)
        bearing_deg, bearing_lbl = _resolve_bearing(message)
        distance_km = _resolve_distance(message)
        origin_name = _extract_origin(message)
        radius_km = _resolve_radius(message)

        # Inherit missing fields from session context (multi-turn)
        if origin_name is None and ctx.get("origin_name"):
            origin_name = ctx["origin_name"]
        if bearing_deg is None and ctx.get("bearing_deg") is not None:
            bearing_deg = ctx["bearing_deg"]
            bearing_lbl = ctx.get("bearing_label", bearing_label(bearing_deg))
        if distance_km is None and ctx.get("distance_km") is not None:
            distance_km = ctx["distance_km"]
        if date_iso is None and ctx.get("date"):
            date_iso = ctx["date"]
            date_label = ctx.get("date_label", date_iso)

        # Default date to today if user said "now", "right now", "currently"
        if date_iso is None and re.search(r"\bnow\b|right now|current|today", message, re.IGNORECASE):
            today = dt.date.today()
            date_iso = today.isoformat()
            date_label = "today"

        # Determine what's still missing
        missing = []
        if origin_name is None:
            missing.append("origin")
        if bearing_deg is None and distance_km is not None:
            # Distance given but no direction
            missing.append("direction")
        if distance_km is None and bearing_deg is not None:
            # Direction given but no distance — default to 30 km
            distance_km = 30.0

        needs_clarification = bool(missing)
        clarification_field = missing[0] if missing else None

        return ParsedQuery(
            intent="debris_near_route",
            date=date_iso,
            date_label=date_label,
            origin_name=origin_name,
            bearing_deg=bearing_deg,
            bearing_label=bearing_lbl,
            distance_km=distance_km,
            search_radius_km=radius_km,
            needs_clarification=needs_clarification,
            clarification_field=clarification_field,
            raw_message=message,
        )


class LLMIntentParser(BaseIntentParser):
    """Uses an LLM to extract the JSON intent schema.

    The LLM is given a strict system prompt that ONLY asks it to extract
    parameters — it must never invent debris numbers, distances, or dates.
    """

    _SYSTEM_PROMPT = """You are a parameter extractor for a marine debris query system.
Extract ONLY the following fields from the user's message. Return valid JSON only.
Do NOT add any text outside the JSON.

Schema (all fields optional — use null if not mentioned):
{
  "origin_name": string | null,          // Place name the vessel departs from
  "bearing_deg": number | null,          // 0=North 90=East 180=South 270=West
  "bearing_label": string | null,        // "north","west","southwest" etc.
  "distance_km": number | null,          // Route length in km
  "date": "YYYY-MM-DD" | null,           // Departure date in ISO format
  "date_label": string | null,           // "tomorrow","Friday" etc.
  "search_radius_km": number,            // Buffer around route; default 5
  "intent": "debris_near_route" | "off_topic"
}

Today's date: {today}
Resolve relative dates: "tomorrow" → {tomorrow}
Convert nautical miles to km (×1.852).
If the message is not about marine debris or vessel routes, set intent="off_topic".
Never add explanations or markdown. Return ONLY the JSON object.
"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or "https://api.openai.com/v1"

    def parse(self, message: str, session_context: dict | None = None) -> ParsedQuery:
        import urllib.request

        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)
        system = self._SYSTEM_PROMPT.format(today=today.isoformat(), tomorrow=tomorrow.isoformat())

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "temperature": 0,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
        }).encode()

        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            raw = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw)
        except Exception as exc:
            logger.warning("LLM intent parse failed, falling back to regex: %s", exc)
            return MockIntentParser().parse(message, session_context)

        return ParsedQuery(
            intent=parsed.get("intent", "debris_near_route"),
            date=parsed.get("date"),
            date_label=parsed.get("date_label"),
            origin_name=parsed.get("origin_name"),
            bearing_deg=parsed.get("bearing_deg"),
            bearing_label=parsed.get("bearing_label"),
            distance_km=parsed.get("distance_km"),
            search_radius_km=parsed.get("search_radius_km", 5.0),
            needs_clarification=parsed.get("origin_name") is None,
            clarification_field="origin" if parsed.get("origin_name") is None else None,
            raw_message=message,
        )


def get_intent_parser(llm_provider: str = "mock", api_key: str | None = None, model: str | None = None) -> BaseIntentParser:
    """Factory — return the right parser based on project settings."""
    if llm_provider in ("openai", "anthropic") and api_key:
        return LLMIntentParser(api_key=api_key, model=model or "gpt-4o-mini")
    return MockIntentParser()
