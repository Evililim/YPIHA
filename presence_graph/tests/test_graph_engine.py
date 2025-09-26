from __future__ import annotations

import pytest

from custom_components.presence_graph.const import (
    ATTR_REASON_DECAY,
    ATTR_REASON_SENSOR,
)
from custom_components.presence_graph.graph_engine import GraphEvent


def _event(
    entity_id: str, new_state: str, ts: float, duration: float | None = None
) -> GraphEvent:
    return GraphEvent(
        entity_id=entity_id,
        new_state=new_state,
        old_state="off",
        timestamp=ts,
        duration=duration,
    )


def test_space_activation_sets_occupied(engine, fake_clock):
    evt = _event("binary_sensor.living_motion", "on", fake_clock.time())
    update = engine.process_event(evt)
    assert "living" in update.changed
    state = engine.current_state()
    assert state.occupied["living"]
    assert state.scores["living"] == pytest.approx(1.0)
    fake_clock.advance(60)
    state = engine.current_state()
    assert state.scores["living"] < 1.0


def test_link_propagation(engine, fake_clock):
    engine.process_event(
        _event("binary_sensor.living_motion", "on", fake_clock.time())
    )
    fake_clock.advance(2)
    update = engine.process_event(
        _event("binary_sensor.link_motion", "on", fake_clock.time())
    )
    assert "kitchen" in update.changed
    state = engine.current_state()
    assert state.occupied["kitchen"]


def test_lock_blocks_traversal(engine, fake_clock):
    engine.process_event(
        _event("binary_sensor.living_motion", "on", fake_clock.time())
    )
    engine.process_event(GraphEvent("lock.link", "locked", "unlocked", fake_clock.time()))
    fake_clock.advance(1)
    update = engine.process_event(
        _event("binary_sensor.link_motion", "on", fake_clock.time())
    )
    assert update.changed == []
    state = engine.current_state()
    assert not state.occupied["kitchen"]


def test_global_count_with_exclusion(engine, fake_clock, sample_spaces, sample_links):
    sample_spaces[1].include_in_total = False
    engine.set_model(sample_spaces, sample_links)
    engine.process_event(
        _event("binary_sensor.living_motion", "on", fake_clock.time())
    )
    fake_clock.advance(1)
    engine.process_event(
        _event("binary_sensor.link_motion", "on", fake_clock.time())
    )
    state = engine.current_state()
    assert state.total_estimated == 1


def test_ignore_short_pulse(engine, fake_clock):
    update = engine.process_event(
        _event("binary_sensor.living_motion", "on", fake_clock.time(), duration=0.1)
    )
    assert update.changed == []
    state = engine.current_state()
    assert not state.occupied["living"]


def test_decay_reason_when_idle(engine, fake_clock):
    evt = _event("binary_sensor.living_motion", "on", fake_clock.time())
    update = engine.process_event(evt)
    assert update.reason == ATTR_REASON_SENSOR
    fake_clock.advance(300)
    decayed = engine.process_event(GraphEvent("unknown", "off", "on", fake_clock.time()))
    assert decayed.reason == ATTR_REASON_DECAY
