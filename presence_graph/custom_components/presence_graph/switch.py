"""Switch entities controlling inclusion of spaces in totals."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DATA_MODEL, DOMAIN
from .coordinator import PresenceGraphCoordinator
from .model import Space


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
    spaces: list[Space] = data[DATA_MODEL]["spaces"]
    entities = [PresenceGraphSpaceIncludeSwitch(coordinator, space, entry) for space in spaces]
    async_add_entities(entities)


class PresenceGraphSpaceIncludeSwitch(CoordinatorEntity[PresenceGraphCoordinator], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PresenceGraphCoordinator, space: Space, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._space = space
        self._attr_unique_id = f"{entry.entry_id}_{space.id}_include"
        self._attr_name = f"Include {space.name}"

    @property
    def is_on(self) -> bool:
        return self._space.include_in_total

    async def async_turn_on(self, **kwargs) -> None:  # type: ignore[override]
        await self.coordinator.async_set_space_included(self._space.id, True)
        self._space.include_in_total = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:  # type: ignore[override]
        await self.coordinator.async_set_space_included(self._space.id, False)
        self._space.include_in_total = False
        self.async_write_ha_state()
