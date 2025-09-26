"""Presence Graph custom component."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_LINKS,
    CONF_SPACES,
    DATA_COORDINATOR,
    DATA_ENGINE,
    DATA_MODEL,
    DOMAIN,
    PLATFORMS,
    SERVICE_FORCE_SPACE_STATE,
    SERVICE_RELOAD_MODEL,
    SERVICE_SET_SPACE_INCLUDED,
)
from .coordinator import PresenceGraphCoordinator
from .graph_engine import GraphEngine
from .model import Link, Space

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    if not hass.services.has_service(DOMAIN, SERVICE_RELOAD_MODEL):
        async def handle_reload(call: ServiceCall) -> None:
            await _async_reload_all(hass)

        async def handle_include(call: ServiceCall) -> None:
            await _async_set_space_included(hass, call)

        async def handle_force(call: ServiceCall) -> None:
            await _async_force_space_state(hass, call)

        hass.services.async_register(DOMAIN, SERVICE_RELOAD_MODEL, handle_reload)
        hass.services.async_register(DOMAIN, SERVICE_SET_SPACE_INCLUDED, handle_include)
        hass.services.async_register(DOMAIN, SERVICE_FORCE_SPACE_STATE, handle_force)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    model = _entry_model(entry)
    time_source = getattr(hass.loop, "time", None)
    engine = GraphEngine(model["spaces"], model["links"], time_func=time_source or time.monotonic)
    coordinator = PresenceGraphCoordinator(hass, entry, engine)
    await coordinator.async_setup(model["spaces"], model["links"])

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ENGINE: engine,
        DATA_COORDINATOR: coordinator,
        DATA_MODEL: model,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
        await coordinator.async_unload()
    return unload_ok


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    model = _entry_model(entry)
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
    await coordinator.async_reset(model["spaces"], model["links"])
    data[DATA_MODEL] = model


async def _async_reload_all(hass: HomeAssistant) -> None:
    for _entry_id, data in list(hass.data.get(DOMAIN, {}).items()):
        coordinator: PresenceGraphCoordinator = data[DATA_COORDINATOR]
        model = _entry_model(coordinator.config_entry)
        await coordinator.async_reset(model["spaces"], model["links"])
        data[DATA_MODEL] = model


async def _async_set_space_included(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = _first_entry(hass)
    if entry is None:
        raise ValueError("Presence Graph is not configured")
    coordinator: PresenceGraphCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    await coordinator.async_set_space_included(call.data["space_id"], call.data["include"])


async def _async_force_space_state(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = _first_entry(hass)
    if entry is None:
        raise ValueError("Presence Graph is not configured")
    coordinator: PresenceGraphCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    await coordinator.async_force_space_state(
        call.data["space_id"], call.data["occupied"], call.data.get("score")
    )


def _first_entry(hass: HomeAssistant) -> ConfigEntry | None:
    domain_entries = hass.config_entries.async_entries(DOMAIN)
    return domain_entries[0] if domain_entries else None


def _entry_model(entry: ConfigEntry) -> dict[str, list[Any]]:
    raw_spaces = entry.options.get(CONF_SPACES, entry.data.get(CONF_SPACES, []))
    raw_links = entry.options.get(CONF_LINKS, entry.data.get(CONF_LINKS, []))
    spaces = [Space(**space) for space in raw_spaces]
    links = [Link(**link) for link in raw_links]
    return {"spaces": spaces, "links": links}
