"""Coordinator for the Presence Graph integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_CHANGED,
    ATTR_LINK,
    ATTR_REASON,
    ATTR_SOURCE_ENTITY,
    ATTR_SPACE,
    ATTR_TOTAL_ESTIMATED,
    DOMAIN,
    EVENT_PRESENCE_GRAPH_UPDATE,
)
from .graph_engine import GraphEngine, GraphEvent
from .model import Link, PresenceState, Space

_LOGGER = logging.getLogger(__name__)


class PresenceGraphCoordinator(DataUpdateCoordinator[PresenceState]):
    """Update coordinator that orchestrates the graph engine."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, engine: GraphEngine) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.config_entry = config_entry
        self.engine = engine
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._entity_map: dict[str, str] = {}

    async def async_setup(self, spaces: list[Space], links: list[Link]) -> None:
        """Initialise listeners according to the configured model."""

        await self.async_refresh()
        self._build_entity_index(spaces, links)
        self._unsubscribe()
        self._unsubscribers.append(
            async_track_state_change_event(
                self.hass, list(self._entity_map), self._handle_state_event
            )
        )

    async def async_reset(self, spaces: list[Space], links: list[Link]) -> None:
        """Rebuild the engine model and restart listeners."""

        _LOGGER.debug(
            "Resetting presence graph with %s spaces and %s links",
            len(spaces),
            len(links),
        )
        self.engine.set_model(spaces, links)
        await self.async_setup(spaces, links)

    async def async_unload(self) -> None:
        self._unsubscribe()

    async def _async_update_data(self) -> PresenceState:
        return self.engine.current_state()

    # ------------------------------------------------------------------
    def _unsubscribe(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _build_entity_index(self, spaces: list[Space], links: list[Link]) -> None:
        self._entity_map.clear()
        for space in spaces:
            for entity in space.motion_entities + space.presence_entities:
                self._entity_map[entity] = space.id
        for link in links:
            for entity in link.motion_entities + link.contact_entities + link.lock_entities:
                self._entity_map[entity] = link.id

    def _handle_state_event(self, event: Event) -> None:
        entity_id: str = event.data.get("entity_id")
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        if entity_id not in self._entity_map or new_state is None:
            return
        loop_time = getattr(self.hass.loop, "time", None)
        timestamp = (
            new_state.last_changed.timestamp()
            if new_state.last_changed
            else (loop_time() if loop_time else 0.0)
        )
        duration: float | None = None
        if old_state is not None and new_state.last_changed and old_state.last_changed:
            duration = (new_state.last_changed - old_state.last_changed).total_seconds()

        graph_event = GraphEvent(
            entity_id=entity_id,
            new_state=new_state.state,
            old_state=old_state.state if old_state is not None else None,
            timestamp=timestamp,
            duration=duration,
        )
        update = self.engine.process_event(graph_event)
        self.async_set_updated_data(update.state)
        self._fire_update_event(update, entity_id)

    def _fire_update_event(self, update: Any, entity_id: str) -> None:
        state = update.state
        payload = {
            ATTR_CHANGED: update.changed,
            ATTR_REASON: update.reason,
            ATTR_SOURCE_ENTITY: entity_id,
            ATTR_TOTAL_ESTIMATED: state.total_estimated,
            ATTR_SPACE: update.space,
            ATTR_LINK: update.link,
        }
        self.hass.bus.async_fire(EVENT_PRESENCE_GRAPH_UPDATE, payload)

    async def async_set_space_included(self, space_id: str, include: bool) -> None:
        if space_id not in self.engine.space_ids():
            raise ValueError(f"Unknown space: {space_id}")
        options = dict(self.config_entry.options)
        spaces_data = [dict(item) for item in options.get("spaces", [])]
        for space in spaces_data:
            if space["id"] == space_id:
                space["include_in_total"] = include
                break
        options["spaces"] = spaces_data
        await self.hass.config_entries.async_update_entry(self.config_entry, options=options)
        self.engine.set_space_inclusion(space_id, include)
        self.async_set_updated_data(self.engine.current_state())

    async def async_force_space_state(
        self, space_id: str, occupied: bool, score: float | None = None
    ) -> None:
        update = self.engine.force_space_state(space_id, occupied, score)
        self.async_set_updated_data(update.state)
        self._fire_update_event(update, "service.force_space_state")
