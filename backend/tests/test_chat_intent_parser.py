"""Tests for chat intent parser — date resolution, bearing conversion, distance parsing."""
from __future__ import annotations

import datetime as dt
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.chat.intent_parser import MockIntentParser, _resolve_date, _resolve_bearing, _resolve_distance

TODAY = dt.date(2026, 10, 8)   # Fixed date for deterministic tests
TOMORROW = TODAY + dt.timedelta(days=1)

parser = MockIntentParser()


# ── Date resolution ───────────────────────────────────────────────────────────

def test_date_today():
    iso, label = _resolve_date("I'm heading out today", today=TODAY)
    assert iso == TODAY.isoformat()
    assert label == "today"


def test_date_tomorrow():
    iso, label = _resolve_date("Leaving tomorrow morning", today=TODAY)
    assert iso == TOMORROW.isoformat()
    assert label == "tomorrow"


def test_date_day_after_tomorrow():
    iso, _ = _resolve_date("I'll go day after tomorrow", today=TODAY)
    assert iso == (TODAY + dt.timedelta(days=2)).isoformat()


def test_date_this_weekend():
    iso, _ = _resolve_date("planning for this weekend", today=TODAY)
    # Saturday of the current week
    days_to_sat = (5 - TODAY.weekday()) % 7
    assert iso == (TODAY + dt.timedelta(days=days_to_sat)).isoformat()


def test_date_weekday_friday():
    iso, label = _resolve_date("Heading out on Friday", today=TODAY)
    # TODAY is Thursday 2026-10-08, Friday is the next day
    assert iso is not None
    assert "friday" in label.lower()


def test_date_none():
    iso, label = _resolve_date("heading west 40 km — any debris?", today=TODAY)
    # No date mentioned — should return None
    assert iso is None


# ── Bearing resolution ────────────────────────────────────────────────────────

def test_bearing_west():
    deg, label = _resolve_bearing("heading west 40 km")
    assert deg == pytest.approx(270.0)
    assert "west" in label.lower()


def test_bearing_northeast():
    deg, label = _resolve_bearing("going northeast towards the fishing grounds")
    assert deg == pytest.approx(45.0)


def test_bearing_south():
    deg, label = _resolve_bearing("steaming south")
    assert deg == pytest.approx(180.0)


def test_bearing_sw():
    deg, label = _resolve_bearing("heading sw from the port")
    assert deg == pytest.approx(225.0)


def test_bearing_none():
    deg, _ = _resolve_bearing("leaving Mundra tomorrow morning")
    assert deg is None


# ── Distance resolution ───────────────────────────────────────────────────────

def test_distance_km():
    d = _resolve_distance("heading west for 40 km")
    assert d == pytest.approx(40.0)


def test_distance_nautical_miles():
    d = _resolve_distance("25 nautical miles southwest")
    assert d == pytest.approx(25 * 1.852, rel=0.01)


def test_distance_nm_abbrev():
    d = _resolve_distance("20 nm heading south")
    assert d == pytest.approx(20 * 1.852, rel=0.01)


def test_distance_miles():
    d = _resolve_distance("30 miles west")
    assert d == pytest.approx(30 * 1.60934, rel=0.01)


def test_distance_none():
    d = _resolve_distance("leaving Mundra tomorrow morning")
    assert d is None


# ── Full parse scenarios ──────────────────────────────────────────────────────

def test_full_parse_vessel_query():
    q = parser.parse(
        "I'm leaving from the Gulf of Kutch tomorrow morning heading west for 40 km. "
        "How much debris will be near me?"
    )
    assert q.intent == "debris_near_route"
    assert q.origin_name is not None
    assert "kutch" in q.origin_name.lower()
    assert q.bearing_deg == pytest.approx(270.0)
    assert q.distance_km == pytest.approx(40.0)
    assert q.needs_clarification is False


def test_parse_off_topic():
    q = parser.parse("What is the capital of France?")
    assert q.intent == "off_topic"


def test_parse_missing_origin():
    q = parser.parse("heading west 40 km tomorrow")
    assert q.needs_clarification is True
    assert q.clarification_field == "origin"


def test_parse_missing_direction_with_distance():
    q = parser.parse("leaving Mundra tomorrow for 40 km")
    # Distance present but direction missing → should ask for direction
    assert q.needs_clarification is True
    assert q.clarification_field == "direction"


def test_session_context_inheritance():
    """Second message inherits origin from first."""
    ctx = {"origin_name": "Kandla", "bearing_deg": 270.0, "bearing_label": "west", "distance_km": 30.0}
    q = parser.parse("What about tomorrow instead?", session_context=ctx)
    assert q.origin_name == "Kandla"
    assert q.bearing_deg == pytest.approx(270.0)
