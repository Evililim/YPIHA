from __future__ import annotations

import pytest

from custom_components.presence_graph.binary_sensor import PresenceGraphSpaceBinarySensor
from custom_components.presence_graph.const import (
    ATTR_INCLUDE_IN_TOTAL,
    ATTR_LAST_EVENT,
    ATTR_SCORE,
    ATTR_SPACE_COUNTS,
    ATTR_TOTAL_ESTIMATED,
)
from custom_components.presence_graph.model import PresenceState, Space
from custom_components.presence_graph.sensors import (
    PresenceGraphSpaceCountSensor,
    PresenceGraphTotalSensor,
)
from custom_components.presence_graph.switch import PresenceGraphSpaceIncludeSwitch


class DummyCoordinator:
    def __init__(self, data: PresenceState) -> None:
        self.data = data
        self.calls: list[tuple[str, bool]] = []
        self.config_entry = type("ConfigEntry", (), {"entry_id": "entry"})()

    async def async_set_space_included(self, space_id: str, include: bool) -> None:
        self.calls.append((space_id, include))


@pytest.fixture
def presence_state() -> PresenceState:
    return PresenceState(
        occupied={"living": True, "kitchen": False},
        scores={"living": 0.9, "kitchen": 0.1},
        total_estimated=1,
        last_event_ts={"living": 1000.0, "kitchen": 0.0},
        space_counts={"living": 1, "kitchen": 0},
    )


def test_binary_sensor_attributes(presence_state):
    coordinator = DummyCoordinator(presence_state)
    space = Space(id="living", name="Living", motion_entities=["binary_sensor.motion"])
    entity = PresenceGraphSpaceBinarySensor(coordinator, space, ["kitchen"])
    attrs = entity.extra_state_attributes
    assert attrs[ATTR_SCORE] == pytest.approx(0.9)
    assert ATTR_LAST_EVENT in attrs
    assert attrs[ATTR_INCLUDE_IN_TOTAL]


def test_total_sensor_attributes(presence_state):
    coordinator = DummyCoordinator(presence_state)
    entry = type("Entry", (), {"entry_id": "entry"})()
    entity = PresenceGraphTotalSensor(coordinator, entry)
    attrs = entity.extra_state_attributes
    assert attrs[ATTR_TOTAL_ESTIMATED] == 1
    assert attrs[ATTR_SPACE_COUNTS]["living"] == 1


def test_space_count_sensor_value(presence_state):
    coordinator = DummyCoordinator(presence_state)
    entry = type("Entry", (), {"entry_id": "entry"})()
    sensor = PresenceGraphSpaceCountSensor(coordinator, entry)
    assert sensor.native_value != "-"


def test_switch_updates_inclusion(presence_state):
    coordinator = DummyCoordinator(presence_state)
    entry = type("Entry", (), {"entry_id": "entry"})()
    space = Space(id="living", name="Living")
    switch = PresenceGraphSpaceIncludeSwitch(coordinator, space, entry)
    import asyncio

    asyncio.run(switch.async_turn_off())
    assert coordinator.calls == [("living", False)]
    assert not space.include_in_total
