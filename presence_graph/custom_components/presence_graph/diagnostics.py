"""Diagnostics for the Presence Graph integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DATA_ENGINE, DOMAIN
from .coordinator import PresenceGraphCoordinator
from .graph_engine import GraphEngine


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, object]:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
    engine: GraphEngine = data[DATA_ENGINE]
    state = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "entry_id": entry.entry_id,
        },
        "graph": engine.describe(),
        "state": state.as_dict() if state else {},
    }
