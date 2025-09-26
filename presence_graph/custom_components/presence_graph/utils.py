"""Utility helpers for Presence Graph."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import voluptuous as vol


def slugify(value: str) -> str:
    """Return a simple slugified representation."""

    normalized = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def ensure_unique_ids(items: Iterable[str]) -> None:
    """Validate that the iterable contains unique identifiers."""

    seen: set[str] = set()
    for item in items:
        if item in seen:
            raise vol.Invalid(f"Duplicate identifier: {item}")
        seen.add(item)


def as_bool(value: Any) -> bool:
    """Coerce a Home Assistant state value to boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"on", "open", "true", "locked", "home"}
    return False


def is_on_state(value: Any) -> bool:
    """Return True when the provided value represents an active state."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value > 0
    if isinstance(value, str):
        lowered = value.lower()
        return lowered in {"on", "open", "true", "home", "locked", "unlocked"}
    return False


def state_is_locked(value: Any) -> bool:
    """Determine whether the lock entity is locking traversals."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"on", "locked", "true"}
    return False


def human_readable_duration(seconds: float) -> str:
    """Convert seconds into a compact string used in diagnostics."""

    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, remaining = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{remaining:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def sorted_unique(items: Iterable[str]) -> list[str]:
    """Return sorted unique values preserving order of first appearance."""

    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
