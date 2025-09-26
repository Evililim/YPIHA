"""Common test fixtures and Home Assistant stubs."""
from __future__ import annotations

import pathlib
import sys
import types
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_module(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    return module


# ---------------------------------------------------------------------------
# Minimal Home Assistant stubs
# ---------------------------------------------------------------------------
ha = _ensure_module("homeassistant")
core = _ensure_module("homeassistant.core")
config_entries = _ensure_module("homeassistant.config_entries")
helpers = _ensure_module("homeassistant.helpers")
helpers.__path__ = []  # mark as package
helpers_event = types.ModuleType("homeassistant.helpers.event")
helpers_update = types.ModuleType("homeassistant.helpers.update_coordinator")
helpers_typing = types.ModuleType("homeassistant.helpers.typing")
components = _ensure_module("homeassistant.components")
components.__path__ = []
binary_sensor_module = types.ModuleType("homeassistant.components.binary_sensor")
sensor_module = types.ModuleType("homeassistant.components.sensor")
switch_module = types.ModuleType("homeassistant.components.switch")

# Voluptuous stub -----------------------------------------------------------
voluptuous = types.ModuleType("voluptuous")


class Invalid(Exception):
    pass


class Marker:
    def __init__(self, key: str, default: Any | None = None) -> None:
        self.key = key
        self.default = default


class Required(Marker):
    pass


class Optional(Marker):
    pass


class Schema:
    def __init__(self, definition: Any) -> None:
        self.definition = definition

    def __call__(self, value: Any) -> Any:
        if isinstance(self.definition, dict):
            if not isinstance(value, dict):
                raise Invalid("Expected mapping")
            result: dict[str, Any] = {}
            for key, _validator in self.definition.items():
                if isinstance(key, Required):
                    if key.key not in value:
                        raise Invalid(f"Missing required key {key.key}")
                    result[key.key] = value[key.key]
                elif isinstance(key, Optional):
                    if key.key in value:
                        result[key.key] = value[key.key]
                    elif key.default is not None:
                        default = key.default
                        result[key.key] = default() if callable(default) else default
                else:
                    result[key] = value.get(key)
            return result
        return value


voluptuous.Invalid = Invalid
voluptuous.Schema = Schema
voluptuous.Required = Required
voluptuous.Optional = Optional
sys.modules["voluptuous"] = voluptuous


def callback(func: Callable) -> Callable:
    return func


class ServiceCall:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}


class State:
    def __init__(self, state: Any, last_changed: datetime | None = None) -> None:
        self.state = state
        self.last_changed = last_changed or datetime.utcnow()


class Event:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


class EventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def async_fire(self, event_type: str, event_data: dict[str, Any]) -> None:
        self.events.append((event_type, event_data))


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: set[tuple[str, str]] = set()

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self._services

    def async_register(self, domain: str, service: str, handler: Callable[..., Any]) -> None:
        self._services.add((domain, service))


class ConfigEntriesManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._entries: list[ConfigEntry] = []

    def async_entries(self, domain: str) -> list[ConfigEntry]:
        return [entry for entry in self._entries if entry.domain == domain]

    async def async_forward_entry_setups(self, entry: ConfigEntry, platforms: list[str]) -> None:
        entry._forwarded = list(platforms)

    async def async_unload_platforms(self, entry: ConfigEntry, platforms: list[str]) -> bool:
        return True

    async def async_update_entry(self, entry: ConfigEntry, *, options: dict[str, Any]) -> None:
        entry.options = options

    def add_entry(self, entry: ConfigEntry) -> None:
        self._entries.append(entry)


class HomeAssistant:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.services = ServiceRegistry()
        self.bus = EventBus()
        self.loop = types.SimpleNamespace(time=lambda: 0.0)
        self.config_entries = ConfigEntriesManager(self)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return "<HomeAssistantStub>"


@dataclass
class ConfigEntry:
    data: dict[str, Any]
    options: dict[str, Any] | None = None
    title: str = "Presence Graph"
    domain: str = "presence_graph"
    entry_id: str = "test-entry"

    def __post_init__(self) -> None:
        if self.options is None:
            self.options = {}
        self._update_listeners: list[Callable[[HomeAssistant, ConfigEntry], Any]] = []
        self._on_unload: list[Callable[[], Any]] = []

    def add_update_listener(
        self, listener: Callable[[HomeAssistant, ConfigEntry], Any]
    ) -> Callable[[HomeAssistant, ConfigEntry], Any]:
        self._update_listeners.append(listener)
        return listener

    def async_on_unload(self, callback: Callable[[], Any]) -> None:
        self._on_unload.append(callback)


class FlowResult(dict):
    pass


class ConfigFlow:
    def __init_subclass__(cls, **kwargs: Any) -> None:  # type: ignore[override]
        cls.domain = kwargs.pop("domain", getattr(cls, "domain", None))
        super().__init_subclass__()

    async def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any,
        errors: dict[str, str] | None = None,
        description_placeholders: dict[str, str] | None = None,
    ) -> FlowResult:
        return FlowResult(
            {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
                "description_placeholders": description_placeholders or {},
            }
        )

    async def async_create_entry(self, *, title: str, data: dict[str, Any]) -> FlowResult:
        return FlowResult({"type": "create_entry", "title": title, "data": data})


class OptionsFlow:
    async def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any,
        errors: dict[str, str] | None = None,
        description_placeholders: dict[str, str] | None = None,
    ) -> FlowResult:
        return FlowResult(
            {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
                "description_placeholders": description_placeholders or {},
            }
        )

    async def async_create_entry(self, *, title: str, data: dict[str, Any]) -> FlowResult:
        return FlowResult({"type": "create_entry", "title": title, "data": data})



class DataUpdateCoordinator:
    def __init__(
        self, hass: HomeAssistant, logger: Any, *, name: str, update_interval: Any
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: Any | None = None

    def __class_getitem__(
        cls, _item: Any
    ) -> type[DataUpdateCoordinator]:  # pragma: no cover - typing helper
        return cls

    async def async_refresh(self) -> None:
        self.data = await self._async_update_data()

    def async_set_updated_data(self, data: Any) -> None:
        self.data = data

    async def _async_update_data(self) -> Any | None:  # pragma: no cover - overridden in subclasses
        return self.data


class CoordinatorEntity:
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id: str | None = None
        self._attr_name: str | None = None

    def __class_getitem__(
        cls, _item: Any
    ) -> type[CoordinatorEntity]:  # pragma: no cover - typing helper
        return cls

    def async_write_ha_state(self) -> None:
        pass


class BinarySensorEntity:
    pass


class BinarySensorDeviceClass:
    OCCUPANCY = "occupancy"


class SensorEntity:
    pass


class SensorStateClass:
    MEASUREMENT = "measurement"


class SwitchEntity:
    pass


helpers_event.async_track_state_change_event = lambda hass, entity_ids, action: (lambda: None)
helpers_update.DataUpdateCoordinator = DataUpdateCoordinator
helpers_update.CoordinatorEntity = CoordinatorEntity
sensor_module.SensorEntity = SensorEntity
sensor_module.SensorStateClass = SensorStateClass
binary_sensor_module.BinarySensorEntity = BinarySensorEntity
binary_sensor_module.BinarySensorDeviceClass = BinarySensorDeviceClass
switch_module.SwitchEntity = SwitchEntity

ha.core = core
ha.config_entries = config_entries
ha.helpers = helpers
ha.components = components

core.callback = callback
core.HomeAssistant = HomeAssistant
core.ServiceCall = ServiceCall
core.State = State
core.Event = Event
core.CALLBACK_TYPE = Callable[..., None]

config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
config_entries.ConfigEntry = ConfigEntry
config_entries.FlowResult = FlowResult

helpers.update_coordinator = helpers_update
helpers.event = helpers_event
helpers.typing = helpers_typing
components.binary_sensor = binary_sensor_module
components.sensor = sensor_module
components.switch = switch_module

sys.modules["homeassistant.helpers.event"] = helpers_event
sys.modules["homeassistant.helpers.update_coordinator"] = helpers_update
sys.modules["homeassistant.helpers.typing"] = helpers_typing
sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_module
sys.modules["homeassistant.components.sensor"] = sensor_module
sys.modules["homeassistant.components.switch"] = switch_module


@pytest.fixture
def fake_clock() -> ClockStub:
    return ClockStub()


class ClockStub:
    def __init__(self) -> None:
        self._value = 0.0

    def time(self) -> float:
        return self._value

    def advance(self, seconds: float) -> None:
        self._value += seconds


@pytest.fixture
def sample_spaces() -> list:
    from custom_components.presence_graph.model import Space

    return [
        Space(
            id="living",
            name="Living Room",
            motion_entities=["binary_sensor.living_motion"],
            timeout_s=60,
        ),
        Space(
            id="kitchen",
            name="Kitchen",
            motion_entities=["binary_sensor.kitchen_motion"],
            timeout_s=90,
        ),
    ]


@pytest.fixture
def sample_links() -> list:
    from custom_components.presence_graph.model import Link

    return [
        Link(
            id="living_kitchen",
            name="Living to Kitchen",
            from_space="living",
            to_space="kitchen",
            motion_entities=["binary_sensor.link_motion"],
            contact_entities=["binary_sensor.link_contact"],
            lock_entities=["lock.link"],
        )
    ]


@pytest.fixture
def engine(sample_spaces, sample_links, fake_clock):
    from custom_components.presence_graph.graph_engine import GraphEngine

    return GraphEngine(sample_spaces, sample_links, time_func=fake_clock.time)
