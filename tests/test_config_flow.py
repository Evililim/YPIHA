from __future__ import annotations

import json

from homeassistant.config_entries import ConfigEntry

from custom_components.presence_graph.config_flow import (
    PresenceGraphConfigFlow,
    PresenceGraphOptionsFlowHandler,
)
from custom_components.presence_graph.const import CONF_LINKS, CONF_SPACES


def test_full_config_flow():
    flow = PresenceGraphConfigFlow()
    import asyncio

    form = asyncio.run(flow.async_step_user(None))
    assert form["type"] == "form"
    asyncio.run(flow.async_step_user({"title": "Maison"}))
    spaces_payload = "Salon\nCuisine"
    asyncio.run(flow.async_step_spaces({"spaces": spaces_payload}))
    links_payload = json.dumps(
        [
            {
                "name": "Porte",
                "from_space": "salon",
                "to_space": "cuisine",
                "motion_entities": ["binary_sensor.porte"],
            }
        ]
    )
    asyncio.run(flow.async_step_links({"links": links_payload}))
    summary = asyncio.run(flow.async_step_summary({}))
    assert summary["type"] == "create_entry"
    assert len(summary["data"][CONF_SPACES]) == 2
    assert summary["data"][CONF_SPACES][0]["id"] == "salon"
    assert len(summary["data"][CONF_LINKS]) == 1


def test_options_flow_update():
    entry = ConfigEntry(data={CONF_SPACES: [], CONF_LINKS: []})
    handler = PresenceGraphOptionsFlowHandler(entry)
    import asyncio

    form = asyncio.run(handler.async_step_init(None))
    assert form["type"] == "form"
    spaces = json.dumps([{ "name": "Chambre" }])
    links = json.dumps([])
    result = asyncio.run(handler.async_step_init({"spaces": spaces, "links": links}))
    assert result["type"] == "create_entry"
    assert result["data"][CONF_SPACES][0]["id"] == "chambre"


def test_parse_spaces_from_comma_separated_list():
    from custom_components.presence_graph.config_flow import _parse_spaces

    payload = "Salon, Cuisine, Bureau"
    spaces = _parse_spaces(payload)
    assert [space["name"] for space in spaces] == ["Salon", "Cuisine", "Bureau"]
    assert [space["id"] for space in spaces] == ["salon", "cuisine", "bureau"]
