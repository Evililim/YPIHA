from __future__ import annotations

from custom_components.presence_graph.graph_engine import GraphEvent


def test_total_estimation_clusters(engine, fake_clock):
    engine.process_event(GraphEvent("binary_sensor.living_motion", "on", "off", fake_clock.time()))
    fake_clock.advance(1)
    engine.process_event(GraphEvent("binary_sensor.kitchen_motion", "on", "off", fake_clock.time()))
    state = engine.current_state()
    assert state.total_estimated == 1


def test_force_space_state_updates_total(engine):
    update = engine.force_space_state("living", True, 0.8)
    assert update.state.total_estimated == 1
    update = engine.force_space_state("kitchen", True, 0.9)
    assert update.state.total_estimated >= 1


def test_set_space_inclusion(engine):
    engine.set_space_inclusion("kitchen", False)
    engine.force_space_state("living", True, 0.9)
    engine.force_space_state("kitchen", True, 0.9)
    state = engine.current_state()
    assert state.total_estimated == 1
