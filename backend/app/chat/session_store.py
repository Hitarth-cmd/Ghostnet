"""Thread-safe in-memory session store with TTL-based expiry.

Keeps the last N messages per session so the intent parser can resolve
pronouns like "the same route" or "that area".  Sessions expire after
IDLE_MINUTES of inactivity to keep memory usage bounded.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.chat.schemas import ParsedQuery

_IDLE_SECONDS = 30 * 60          # 30 minutes idle → session expires
_MAX_HISTORY_PER_SESSION = 10    # Keep last 10 exchanges per session

_lock = threading.Lock()

# session_id → deque of (timestamp, ParsedQuery|str) pairs
_store: dict[str, deque] = defaultdict(lambda: deque(maxlen=_MAX_HISTORY_PER_SESSION))
_last_seen: dict[str, float] = {}


def add_message(session_id: str, role: str, content: str | dict) -> None:
    """Append a message (user or assistant) to the session history."""
    with _lock:
        _store[session_id].append({"role": role, "content": content, "ts": time.time()})
        _last_seen[session_id] = time.time()


def get_history(session_id: str) -> list[dict]:
    """Return the message history for a session (most-recent N entries)."""
    _evict_expired()
    with _lock:
        return list(_store.get(session_id, []))


def get_last_parsed_query(session_id: str) -> "ParsedQuery | None":
    """Return the most recent successfully parsed query for this session."""
    history = get_history(session_id)
    for entry in reversed(history):
        if entry["role"] == "parsed" and isinstance(entry["content"], dict):
            try:
                from app.chat.schemas import ParsedQuery
                return ParsedQuery(**entry["content"])
            except Exception:
                pass
    return None


def store_parsed_query(session_id: str, query: "ParsedQuery") -> None:
    """Persist the parsed query object so follow-up questions can reference it."""
    with _lock:
        _store[session_id].append({
            "role": "parsed",
            "content": query.model_dump(),
            "ts": time.time(),
        })
        _last_seen[session_id] = time.time()


def _evict_expired() -> None:
    now = time.time()
    with _lock:
        expired = [sid for sid, ts in _last_seen.items() if now - ts > _IDLE_SECONDS]
        for sid in expired:
            _store.pop(sid, None)
            _last_seen.pop(sid, None)
