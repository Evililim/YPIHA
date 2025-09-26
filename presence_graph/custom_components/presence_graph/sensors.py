"""Sensors exposed by the Presence Graph integration."""
from __future__ import annotations

import json
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_METHOD,
    ATTR_OCCUPIED_SPACES,
    ATTR_SPACE_COUNTS,
    ATTR_TOTAL_ESTIMATED,
    ATTR_UPDATED_AT,
    DATA_COORDINATOR,
    DATA_MODEL,
    DOMAIN,
    UPDATE_METHOD,
)
from .coordinator import PresenceGraphCoordinator
from .model import Space


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
    spaces: list[Space] = data[DATA_MODEL]["spaces"]

    entities: list[SensorEntity] = [PresenceGraphTotalSensor(coordinator, entry)]
    if spaces:
        entities.append(PresenceGraphSpaceCountSensor(coordinator, entry))
    async_add_entities(entities)


class PresenceGraphTotalSensor(CoordinatorEntity[PresenceGraphCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "person"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PresenceGraphCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_total"
        self._attr_name = "Total occupants"

    @property
    def native_value(self) -> int:
        state = self.coordinator.data
        return state.total_estimated if state else 0

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self.coordinator.data
        if not state:
            return {}
        occupied = [space_id for space_id, active in state.occupied.items() if active]
        return {
            ATTR_TOTAL_ESTIMATED: state.total_estimated,
            ATTR_SPACE_COUNTS: state.space_counts,
            ATTR_OCCUPIED_SPACES: occupied,
            ATTR_UPDATED_AT: datetime.utcnow().isoformat(),
            ATTR_METHOD: UPDATE_METHOD,
        }


class PresenceGraphSpaceCountSensor(CoordinatorEntity[PresenceGraphCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:account-group"

    def __init__(self, coordinator: PresenceGraphCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_space_counts"
        self._attr_name = "Space counts"

    @property
    def native_value(self) -> str:
        state = self.coordinator.data
        if not state:
            return "-"
        if not state.space_counts:
            return "-"
        return json.dumps(state.space_counts)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self.coordinator.data
        if not state:
            return {}
        occupied = [space_id for space_id, active in state.occupied.items() if active]
        return {
            ATTR_SPACE_COUNTS: state.space_counts,
            ATTR_OCCUPIED_SPACES: occupied,
            ATTR_UPDATED_AT: datetime.utcnow().isoformat(),
            ATTR_METHOD: UPDATE_METHOD,
        }
