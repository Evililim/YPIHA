"""Inference engine for the Presence Graph integration."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Any

from .const import (
    ATTR_REASON_DECAY,
    ATTR_REASON_FORCED,
    ATTR_REASON_LINK,
    ATTR_REASON_SENSOR,
    DEFAULT_DECAY_THRESHOLD,
    DEFAULT_TIMEOUT,
    DEFAULT_TRAVERSAL_LATENCY,
    LINK_EVENT_DEBOUNCE,
    MIN_EVENT_DURATION,
)
from .model import Link, PresenceState, Space
from .utils import ensure_unique_ids, is_on_state, sorted_unique, state_is_locked


@dataclass(slots=True)
class GraphEvent:
    """Representation of an entity event forwarded to the engine."""

    entity_id: str
    new_state: Any
    old_state: Any | None
    timestamp: float
    duration: float | None = None


@dataclass(slots=True)
class GraphUpdate:
    """Information returned after processing an event."""

    state: PresenceState
    changed: list[str]
    reason: str
    source_entity_id: str | None = None
    space: str | None = None
    link: str | None = None


class GraphEngine:
    """Core inference engine operating on the presence graph."""

    def __init__(
        self,
        spaces: Iterable[Space],
        links: Iterable[Link],
        time_func: Callable[[], float],
        decay_threshold: float = DEFAULT_DECAY_THRESHOLD,
    ) -> None:
        self._time_func = time_func
        self._decay_threshold = decay_threshold
        self._spaces: dict[str, Space] = {}
        self._links: dict[str, Link] = {}
        self._entity_index: dict[str, tuple[str, str]] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._link_entities: dict[str, dict[str, set[str]]] = {}
        self._locked_links: set[str] = set()
        self._last_link_event: dict[str, float] = {}
        self._last_reason: str = ATTR_REASON_DECAY
        self._state = PresenceState(occupied={}, scores={}, total_estimated=0, last_event_ts={})
        self.set_model(spaces, links)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def set_model(self, spaces: Iterable[Space], links: Iterable[Link]) -> None:
        """Replace the current model with a new set of spaces and links."""

        space_map = {space.id: space for space in spaces}
        ensure_unique_ids(space_map)
        link_map = {link.id: link for link in links}
        ensure_unique_ids(link_map)

        self._spaces = space_map
        self._links = link_map
        self._adjacency = {sid: set() for sid in space_map}
        self._entity_index.clear()
        self._link_entities = {
            link_id: {"motion": set(), "contact": set(), "lock": set()}
            for link_id in link_map
        }

        for space in space_map.values():
            for entity in sorted_unique(space.motion_entities + space.presence_entities):
                self._entity_index[entity] = ("space", space.id)

        for link in link_map.values():
            if link.from_space not in self._adjacency or link.to_space not in self._adjacency:
                continue
            self._adjacency[link.from_space].add(link.to_space)
            self._adjacency[link.to_space].add(link.from_space)
            for entity in sorted_unique(link.motion_entities):
                self._entity_index[entity] = ("link_motion", link.id)
                self._link_entities[link.id]["motion"].add(entity)
            for entity in sorted_unique(link.contact_entities):
                self._entity_index[entity] = ("link_contact", link.id)
                self._link_entities[link.id]["contact"].add(entity)
            for entity in sorted_unique(link.lock_entities):
                self._entity_index[entity] = ("link_lock", link.id)
                self._link_entities[link.id]["lock"].add(entity)

        self.reset_state()

    def reset_state(self) -> None:
        """Reset the internal dynamic state."""

        self._state = PresenceState(
            occupied=dict.fromkeys(self._spaces, False),
            scores=dict.fromkeys(self._spaces, 0.0),
            total_estimated=0,
            last_event_ts={space_id: float("-inf") for space_id in self._spaces},
            space_counts=dict.fromkeys(self._spaces, 0),
        )
        self._locked_links.clear()
        self._last_link_event.clear()
        self._last_reason = ATTR_REASON_DECAY

    def current_state(self) -> PresenceState:
        """Return the current state snapshot."""

        self._apply_decay(self._time_func())
        return self._state

    def process_event(self, event: GraphEvent) -> GraphUpdate:
        """Process an entity state event and return updated state."""

        mapping = self._entity_index.get(event.entity_id)
        if mapping is None:
            self._apply_decay(event.timestamp)
            return GraphUpdate(self._state, [], ATTR_REASON_DECAY)

        event_type, target_id = mapping
        ts = event.timestamp
        changed: list[str] = []
        self._apply_decay(ts)

        if event.duration is not None and event.duration < MIN_EVENT_DURATION:
            return GraphUpdate(self._state, [], ATTR_REASON_DECAY)

        if event_type == "space":
            if is_on_state(event.new_state):
                changed = self._activate_space(target_id, ts, event.entity_id)
                reason = ATTR_REASON_SENSOR
            else:
                reason = ATTR_REASON_DECAY
        elif event_type == "link_lock":
            reason = self._handle_link_lock(target_id, event)
        else:
            changed = self._handle_link_activity(target_id, ts, event.entity_id)
            reason = ATTR_REASON_LINK

        if changed:
            self._last_reason = reason
            self._recalculate_totals()
        else:
            self._recalculate_totals()
            reason = self._last_reason

        return GraphUpdate(
            self._state,
            changed,
            reason,
            event.entity_id,
            space=mapping[1] if event_type == "space" else None,
            link=target_id if event_type != "space" else None,
        )

    def force_space_state(
        self,
        space_id: str,
        occupied: bool,
        score: float | None = None,
        *,
        reason: str = ATTR_REASON_FORCED,
    ) -> GraphUpdate:
        """Force the state of a space for debugging purposes."""

        if space_id not in self._spaces:
            return GraphUpdate(self._state, [], reason)
        ts = self._time_func()
        score_to_apply = max(
            0.0, min(1.0, score if score is not None else (1.0 if occupied else 0.0))
        )
        self._state.scores[space_id] = score_to_apply
        self._state.occupied[space_id] = (
            occupied if occupied else score_to_apply > self._decay_threshold
        )
        if occupied:
            self._state.last_event_ts[space_id] = ts
        changed = [space_id]
        self._recalculate_totals()
        return GraphUpdate(self._state, changed, reason, space=space_id)

    def set_space_inclusion(self, space_id: str, include: bool) -> None:
        if space_id in self._spaces:
            self._spaces[space_id].include_in_total = include
            self._recalculate_totals()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _activate_space(self, space_id: str, ts: float, entity_id: str) -> list[str]:
        if space_id not in self._spaces:
            return []
        self._state.scores[space_id] = 1.0
        self._state.occupied[space_id] = True
        self._state.last_event_ts[space_id] = ts
        self._state.space_counts[space_id] = 1
        return [space_id]

    def _handle_link_lock(self, link_id: str, event: GraphEvent) -> str:
        locked = state_is_locked(event.new_state)
        if locked:
            self._locked_links.add(link_id)
        else:
            self._locked_links.discard(link_id)
        return ATTR_REASON_LINK

    def _handle_link_activity(self, link_id: str, ts: float, entity_id: str) -> list[str]:
        if link_id not in self._links:
            return []
        if link_id in self._locked_links:
            return []
        last_event_ts = self._last_link_event.get(link_id)
        if last_event_ts is not None and ts - last_event_ts < LINK_EVENT_DEBOUNCE:
            return []
        self._last_link_event[link_id] = ts

        link = self._links[link_id]
        latency = link.traversal_latency_s or DEFAULT_TRAVERSAL_LATENCY
        candidates: list[tuple[str, str]] = [
            (link.from_space, link.to_space),
            (link.to_space, link.from_space),
        ]
        changed: list[str] = []
        for source, target in candidates:
            last_activation = self._state.last_event_ts.get(source, 0.0)
            if last_activation > float("-inf") and ts - last_activation <= latency:
                boost = self._compute_boost(target, ts)
                if boost:
                    changed.append(target)
        return sorted_unique(changed)

    def _compute_boost(self, space_id: str, ts: float) -> bool:
        if space_id not in self._spaces:
            return False
        prev_score = self._state.scores.get(space_id, 0.0)
        new_score = max(prev_score, 0.6)
        if new_score <= prev_score + 1e-6:
            return False
        self._state.scores[space_id] = min(1.0, new_score)
        self._state.last_event_ts[space_id] = ts
        self._state.occupied[space_id] = self._state.scores[space_id] > self._decay_threshold
        if self._state.occupied[space_id]:
            self._state.space_counts[space_id] = 1
        return True

    def _apply_decay(self, now: float) -> None:
        for space_id, space in self._spaces.items():
            last_ts = self._state.last_event_ts.get(space_id, float("-inf"))
            timeout = space.timeout_s or DEFAULT_TIMEOUT
            elapsed = max(0.0, now - last_ts)
            if elapsed >= timeout:
                new_score = 0.0
            else:
                new_score = max(0.0, 1.0 - elapsed / timeout)
            if new_score < self._state.scores.get(space_id, 0.0):
                self._state.scores[space_id] = new_score
                self._state.occupied[space_id] = new_score > self._decay_threshold
                if not self._state.occupied[space_id]:
                    self._state.space_counts[space_id] = 0

    def _recalculate_totals(self) -> None:
        occupied_spaces = [sid for sid, occ in self._state.occupied.items() if occ]
        included = [sid for sid in occupied_spaces if self._spaces[sid].include_in_total]
        space_counts = {sid: (1 if sid in occupied_spaces else 0) for sid in self._spaces}
        self._state.space_counts = space_counts

        if not occupied_spaces:
            self._state.total_estimated = 0
            return

        if not included:
            self._state.total_estimated = 0
            return

        clusters = self._count_clusters(included)
        estimated = max(clusters, 1)
        previous = self._state.total_estimated
        if estimated > previous + 1:
            estimated = previous + 1
        self._state.total_estimated = estimated

    def _count_clusters(self, spaces: list[str]) -> int:
        if not spaces:
            return 0
        remaining = set(spaces)
        visited: set[str] = set()
        clusters = 0
        while remaining:
            current = remaining.pop()
            clusters += 1
            queue: deque[str] = deque([current])
            visited.add(current)
            while queue:
                node = queue.popleft()
                for neighbour in self._adjacency.get(node, set()):
                    if neighbour in visited or neighbour not in remaining:
                        continue
                    visited.add(neighbour)
                    remaining.discard(neighbour)
                    queue.append(neighbour)
        return clusters

    def describe(self) -> dict[str, Any]:
        """Return a diagnostic description of the current graph."""

        return {
            "spaces": {sid: asdict(space) for sid, space in self._spaces.items()},
            "links": {lid: asdict(link) for lid, link in self._links.items()},
            "locked_links": sorted(self._locked_links),
            "adjacency": {sid: sorted(neighbours) for sid, neighbours in self._adjacency.items()},
            "state": self._state.as_dict(),
        }

    def space_ids(self) -> list[str]:
        return list(self._spaces)

    def link_ids(self) -> list[str]:
        return list(self._links)
