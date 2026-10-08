"""Reply generator: turns deterministic debris counts into friendly prose.

The LLM (or template engine) ONLY sees the numbers already computed by
debris_query.py. It must never recompute, estimate, or invent figures.

Two implementations:
  TemplateReplyGenerator  — deterministic, zero API key, always works.
  LLMReplyGenerator       — sends the computed numbers to an LLM API for
                            friendlier prose; falls back to template on error.
"""
from __future__ import annotations

import datetime as dt
import logging
import json
import urllib.request
from abc import ABC, abstractmethod

from app.chat.schemas import DebrisSummary, ParsedQuery

logger = logging.getLogger("ghostnet.chat.reply_generator")

# ─── Clarification prompts ────────────────────────────────────────────────────

_CLARIFICATION_PROMPTS: dict[str, str] = {
    "origin": (
        "I'd love to help! Could you tell me which port or coastal location "
        "you'll be departing from? (e.g., 'Mundra', 'Kandla', 'Okha')"
    ),
    "direction": (
        "Got it — which direction will you be heading? "
        "(e.g., 'west', 'southwest', 'south')"
    ),
    "distance": (
        "How far are you planning to travel along that route? "
        "(e.g., '40 km', '25 nautical miles')"
    ),
    "date": (
        "For which date are you planning this trip? "
        "(e.g., 'tomorrow', 'Friday', 'Oct 15')"
    ),
}

_OFF_TOPIC_REPLY = (
    "I'm the OceanGuard Marine Debris Assistant — I can tell you about "
    "ghost nets and marine debris along your planned vessel route. "
    "Try something like: 'Leaving Mundra tomorrow heading west 40 km — "
    "how much debris will be near me?'"
)


# ─── Template-based generator (no API key needed) ────────────────────────────

class TemplateReplyGenerator:
    """Deterministic template-based reply. Works offline, no API key required."""

    def generate(self, query: ParsedQuery, summary: DebrisSummary | None) -> str:
        if query.intent == "off_topic":
            return _OFF_TOPIC_REPLY

        if query.needs_clarification:
            field = query.clarification_field or "origin"
            return _CLARIFICATION_PROMPTS.get(field, _CLARIFICATION_PROMPTS["origin"])

        if summary is None:
            return (
                "I couldn't retrieve debris data for that route right now. "
                "Please try again or check that the OceanGuard backend is running."
            )

        # Header
        origin = query.origin_name or "your departure point"
        date_lbl = query.date_label or query.date or "the specified date"
        direction = query.bearing_label or "your planned direction"
        dist = f"{query.distance_km:.0f} km" if query.distance_km else "along your route"
        radius = query.search_radius_km

        lines = [
            f"📍 **Route summary** — departing {origin.title()}, "
            f"heading {direction} for {dist} "
            f"(±{radius:.0f} km corridor) on **{date_lbl}**.\n"
        ]

        # Data availability note
        if summary.total_debris == 0:
            if summary.data_date is None:
                lines.append(
                    "✅ No marine debris detections found in the OceanGuard database "
                    "for this corridor. The route appears clear based on current data."
                )
            else:
                lines.append(
                    f"✅ No detections found for **{summary.data_date}** in this corridor. "
                    "Your route looks clear based on available data."
                )
            if summary.nearest_available_date:
                lines.append(
                    f"*Note: The nearest data available was from {summary.nearest_available_date}.*"
                )
            return "\n".join(lines)

        # Debris counts
        lines.append(f"🗑️ **{summary.total_debris} detection(s) found** along your corridor:\n")

        if summary.ghost_nets > 0:
            lines.append(f"• 🪤 **{summary.ghost_nets} ghost net(s)** — highest priority for collection")
        if summary.other_debris > 0:
            lines.append(f"• 🧴 **{summary.other_debris} marine debris item(s)** (plastic/floating waste)")
        if summary.unknown_objects > 0:
            lines.append(f"• ❓ **{summary.unknown_objects} unclassified floating object(s)**")

        # Hotspots
        if summary.hotspots:
            lines.append("\n📍 **Top debris hotspot(s) along your route:**")
            for i, hs in enumerate(summary.hotspots[:3], 1):
                cls_label = hs.object_class.replace("_", " ").title()
                lines.append(
                    f"  {i}. **{hs.count} {cls_label}** — "
                    f"{hs.distance_from_start_km:.1f} km from departure "
                    f"(confidence {hs.confidence_avg * 100:.0f}%)"
                )

        # Date metadata
        if summary.data_date:
            lines.append(f"\n📅 Data from: **{summary.data_date}**")
        if summary.nearest_available_date:
            lines.append(
                f"⚠️ *No data for the exact requested date — "
                f"showing nearest available: {summary.nearest_available_date}*"
            )

        # Recommendation
        if summary.ghost_nets > 0:
            lines.append(
                "\n🚢 **Recommendation:** Ghost nets present — consider bringing "
                "cutting tools and reporting each recovery to the platform."
            )
        elif summary.total_debris > 5:
            lines.append(
                "\n🚢 **Recommendation:** High debris density. Equip for collection "
                "and mark recovered items via the OceanGuard app."
            )
        else:
            lines.append(
                "\n🚢 Moderate debris levels — standard equipment sufficient. "
                "Tap any hotspot marker on the map for exact coordinates."
            )

        lines.append(
            "\n*Data source: OceanGuard Detection Database. "
            "All figures are from verified satellite/sensor detections — "
            "not estimated by AI.*"
        )

        return "\n".join(lines)


# ─── LLM reply generator (OpenAI-compatible) ─────────────────────────────────

class LLMReplyGenerator:
    """Sends the computed numbers to an LLM for friendlier prose.

    The LLM ONLY writes prose — it sees the counts and must not change them.
    Falls back to TemplateReplyGenerator on any API error.
    """

    _SYSTEM_PROMPT = """You are OceanGuard, a helpful marine debris AI assistant.
You will be given a JSON object with EXACT, COMPUTED debris statistics for a vessel route.
Write a friendly, actionable response in markdown using ONLY the numbers provided.
Never change, invent, or estimate debris counts. Never add figures not in the JSON.
Keep your response under 250 words. Use emojis sparingly.
"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or "https://api.openai.com/v1"
        self._template = TemplateReplyGenerator()

    def generate(self, query: ParsedQuery, summary: DebrisSummary | None) -> str:
        if query.intent == "off_topic":
            return _OFF_TOPIC_REPLY
        if query.needs_clarification:
            field = query.clarification_field or "origin"
            return _CLARIFICATION_PROMPTS.get(field, _CLARIFICATION_PROMPTS["origin"])
        if summary is None:
            return self._template.generate(query, None)

        context = {
            "query": query.model_dump(exclude={"raw_message"}),
            "debris_summary": summary.model_dump(),
        }

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
            "temperature": 0.4,
            "max_tokens": 400,
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
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("LLM reply generation failed, using template: %s", exc)
            return self._template.generate(query, summary)


# ─── Factory ──────────────────────────────────────────────────────────────────

def get_reply_generator(
    llm_provider: str = "mock",
    api_key: str | None = None,
    model: str | None = None,
) -> TemplateReplyGenerator | LLMReplyGenerator:
    if llm_provider in ("openai", "anthropic") and api_key:
        return LLMReplyGenerator(api_key=api_key, model=model or "gpt-4o-mini")
    return TemplateReplyGenerator()
