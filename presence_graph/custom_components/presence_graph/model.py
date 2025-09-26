"""Data models for the Presence Graph integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Space:
    """Representation of a logical space/room."""

    id: str
    name: str
    include_in_total: bool = True
    motion_entities: list[str] = field(default_factory=list)
    presence_entities: list[str] = field(default_factory=list)
    timeout_s: int = 120


@dataclass(slots=True)
class Link:
    """Representation of a connection between two spaces."""

    id: str
    name: str
    from_space: str
    to_space: str
    motion_entities: list[str] = field(default_factory=list)
    contact_entities: list[str] = field(default_factory=list)
    lock_entities: list[str] = field(default_factory=list)
    traversal_latency_s: int = 8


@dataclass(slots=True)
class PresenceState:
    """Current inference state of the graph."""

    occupied: dict[str, bool]
    scores: dict[str, float]
    total_estimated: int
    last_event_ts: dict[str, float]
    space_counts: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return {
            "occupied": self.occupied,
            "scores": self.scores,
            "total_estimated": self.total_estimated,
            "last_event_ts": self.last_event_ts,
            "space_counts": self.space_counts,
        }
