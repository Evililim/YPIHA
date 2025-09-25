"""YPIHA integration for Home Assistant."""

from __future__ import annotations

import os

DOMAIN = "ypiha"
_PANEL_URL_PATH = "/ypiha-panel"
_PANEL_ID = "ypiha"


async def async_setup(hass, config):
    """Set up the YPIHA integration with a sidebar panel."""
    panel_dir = os.path.join(os.path.dirname(__file__), "panel")

    hass.http.register_static_path(
        _PANEL_URL_PATH, panel_dir, cache_headers=False, allow_override=True
    )

    frontend = hass.components.frontend

    if _PANEL_ID in frontend.panels:
        frontend.async_remove_panel(_PANEL_ID)

    frontend.async_register_built_in_panel(
        component_name="iframe",
        sidebar_title="YPIHA",
        sidebar_icon="mdi:file-outline",
        config={"url": f"{_PANEL_URL_PATH}/index.html"},
        require_admin=False,
        config_panel_domain=DOMAIN,
        panel_id=_PANEL_ID,
    )

    return True
