"""Binary sensors exposed by the Presence Graph integration."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_INCLUDE_IN_TOTAL,
    ATTR_LAST_EVENT,
    ATTR_LINKED_SPACES,
    ATTR_MOTION_ENTITIES,
    ATTR_PRESENCE_ENTITIES,
    ATTR_SCORE,
    DATA_COORDINATOR,
    DATA_MODEL,
    DOMAIN,
)
from .coordinator import PresenceGraphCoordinator
from .model import Link, Space


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
    model = data[DATA_MODEL]
    spaces: list[Space] = model["spaces"]
    links: list[Link] = model["links"]
    adjacency: dict[str, list[str]] = {space.id: [] for space in spaces}
    for link in links:
        adjacency.setdefault(link.from_space, []).append(link.to_space)
        adjacency.setdefault(link.to_space, []).append(link.from_space)

    sensors = [
        PresenceGraphSpaceBinarySensor(coordinator, space, adjacency.get(space.id, []))
        for space in spaces
    ]
    async_add_entities(sensors)


class PresenceGraphSpaceBinarySensor(
    CoordinatorEntity[PresenceGraphCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self, coordinator: PresenceGraphCoordinator, space: Space, linked: list[str]
    ) -> None:
        super().__init__(coordinator)
        self._space = space
        self._linked = linked
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{space.id}"
        self._attr_name = f"{space.name}"

    @property
    def is_on(self) -> bool:
        state = self.coordinator.data
        return state.occupied.get(self._space.id, False) if state else False

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self.coordinator.data
        if not state:
            return {}
        last_event = state.last_event_ts.get(self._space.id)
        last_event_iso = None
        if last_event:
            last_event_iso = datetime.fromtimestamp(last_event).isoformat()
        return {
            ATTR_SCORE: round(state.scores.get(self._space.id, 0.0), 3),
            ATTR_LAST_EVENT: last_event_iso,
            ATTR_INCLUDE_IN_TOTAL: self._space.include_in_total,
            ATTR_LINKED_SPACES: self._linked,
            ATTR_MOTION_ENTITIES: self._space.motion_entities,
            ATTR_PRESENCE_ENTITIES: self._space.presence_entities,
        }
