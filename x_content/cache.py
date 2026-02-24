"""Session and trending topic cache management.

Persists recent session data (last username, last trending topics)
so the user can resume quickly when restarting the tool.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from x_content import config


def _get_cache_root() -> Path:
    """Get the root cache directory."""
    cache_dir = Path(config.get("profile", {}).get("cache_dir", ".cache/profiles")).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# ── Session state ─────────────────────────────────────────────

SESSION_FILE = "session.json"


def load_session() -> dict:
    """Load the last session state.

    Returns dict with:
      - last_username: str | None
      - last_action: str | None ("optimize" | "discover")
      - updated_at: str (ISO timestamp)
    """
    path = _get_cache_root() / SESSION_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_session(
    username: str | None = None,
    action: str | None = None,
) -> None:
    """Save current session state."""
    path = _get_cache_root() / SESSION_FILE
    existing = load_session()

    if username is not None:
        existing["last_username"] = username
    if action is not None:
        existing["last_action"] = action
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        pass


# ── Trending topics cache ─────────────────────────────────────

TRENDING_DIR = "trending"


def _get_trending_dir() -> Path:
    """Get the trending topics cache directory."""
    d = _get_cache_root() / TRENDING_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _topic_key(topic: str) -> str:
    """Normalize topic string for use as filename."""
    return topic.lower().strip().replace(" ", "_").replace("/", "_")[:60]


def save_trending_topics(
    topic: str,
    raw_response: str,
    parsed_topics: list[dict],
) -> None:
    """Cache Grok's trending topic response for a given topic."""
    path = _get_trending_dir() / f"{_topic_key(topic)}.json"
    data = {
        "topic": topic,
        "raw_response": raw_response,
        "parsed_topics": parsed_topics,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        pass


def load_trending_topics(topic: str, ttl_hours: float = 2.0) -> dict | None:
    """Load cached trending topics if fresh enough.

    Returns dict with: topic, raw_response, parsed_topics, cached_at.
    Returns None if not found or expired.
    """
    path = _get_trending_dir() / f"{_topic_key(topic)}.json"
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Check TTL
    cached_at = data.get("cached_at", "")
    if cached_at:
        try:
            cache_time = datetime.fromisoformat(cached_at)
            age_hours = (datetime.now(timezone.utc) - cache_time).total_seconds() / 3600
            if age_hours > ttl_hours:
                return None
        except (ValueError, TypeError):
            return None

    return data


def list_recent_trending() -> list[dict]:
    """List all cached trending topic entries, sorted by most recent.

    Returns list of dicts with: topic, cached_at, topic_count.
    """
    trending_dir = _get_trending_dir()
    entries = []

    for f in trending_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text("utf-8"))
            entries.append({
                "topic": data.get("topic", f.stem),
                "cached_at": data.get("cached_at", ""),
                "topic_count": len(data.get("parsed_topics", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue

    # Sort by cached_at descending
    entries.sort(key=lambda e: e.get("cached_at", ""), reverse=True)
    return entries
