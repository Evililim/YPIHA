"""Config flow for the Presence Graph integration."""
from __future__ import annotations

import inspect
import json
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from .const import CONF_LINKS, CONF_SPACES, DOMAIN
from .utils import ensure_unique_ids, slugify

SPACE_FIELD = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Optional("id"): str,
        vol.Optional("include_in_total", default=True): bool,
        vol.Optional("timeout_s", default=120): int,
        vol.Optional("motion_entities", default=list): list,
        vol.Optional("presence_entities", default=list): list,
    }
)

LINK_FIELD = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Optional("id"): str,
        vol.Required("from_space"): str,
        vol.Required("to_space"): str,
        vol.Optional("motion_entities", default=list): list,
        vol.Optional("contact_entities", default=list): list,
        vol.Optional("lock_entities", default=list): list,
        vol.Optional("traversal_latency_s", default=8): int,
    }
)


class PresenceGraphConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._title = "Presence Graph"
        self._spaces: list[dict[str, Any]] = []
        self._links: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is None:
            return await _ensure(self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required("title", default=self._title): str}),
            ))
        self._title = user_input["title"]
        return await self.async_step_spaces()

    async def async_step_spaces(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is None:
            return await _ensure(self.async_show_form(
                step_id="spaces",
                data_schema=vol.Schema({vol.Required("spaces"): str}),
                description_placeholders={
                    "hint": (
                        "Provide a JSON array of spaces or simply list their names, one per line."
                    )
                },
            ))
        try:
            spaces = _parse_spaces(user_input["spaces"])
        except ValueError:
            return await _ensure(self.async_show_form(
                step_id="spaces",
                data_schema=vol.Schema({vol.Required("spaces"): str}),
                errors={"base": "invalid_json"},
            ))
        errors = _validate_spaces(spaces)
        if errors:
            return await _ensure(self.async_show_form(
                step_id="spaces",
                data_schema=vol.Schema({vol.Required("spaces"): str}),
                errors={"base": errors[0]},
            ))
        self._spaces = spaces
        return await self.async_step_links()

    async def async_step_links(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is None:
            return await _ensure(self.async_show_form(
                step_id="links",
                data_schema=vol.Schema({vol.Optional("links", default="[]"): str}),
            ))
        try:
            links = _parse_links(user_input.get("links", "[]"))
        except ValueError:
            return await _ensure(self.async_show_form(
                step_id="links",
                data_schema=vol.Schema({vol.Optional("links", default="[]"): str}),
                errors={"base": "invalid_json"},
            ))
        errors = _validate_links(self._spaces, links)
        if errors:
            return await _ensure(self.async_show_form(
                step_id="links",
                data_schema=vol.Schema({vol.Optional("links", default="[]"): str}),
                errors={"base": errors[0]},
            ))
        self._links = links
        return await self.async_step_summary()

    async def async_step_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is None:
            return await _ensure(self.async_show_form(
                step_id="summary",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "spaces": str(len(self._spaces)),
                    "links": str(len(self._links)),
                },
            ))
        return await _ensure(self.async_create_entry(
            title=self._title,
            data={CONF_SPACES: self._spaces, CONF_LINKS: self._links},
        ))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        return PresenceGraphOptionsFlowHandler(config_entry)


class PresenceGraphOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        current_spaces = self.config_entry.options.get(
            CONF_SPACES, self.config_entry.data.get(CONF_SPACES, [])
        )
        current_links = self.config_entry.options.get(
            CONF_LINKS, self.config_entry.data.get(CONF_LINKS, [])
        )
        if user_input is None:
            return await _ensure(self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required("spaces", default=json.dumps(current_spaces, indent=2)): str,
                        vol.Required("links", default=json.dumps(current_links, indent=2)): str,
                    }
                ),
            ))
        try:
            spaces = _parse_spaces(user_input["spaces"])
            links = _parse_links(user_input["links"])
        except ValueError:
            return await _ensure(self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required("spaces", default=user_input.get("spaces", "[]")): str,
                        vol.Required("links", default=user_input.get("links", "[]")): str,
                    }
                ),
                errors={"base": "invalid_json"},
            ))
        space_errors = _validate_spaces(spaces)
        link_errors = _validate_links(spaces, links)
        if space_errors or link_errors:
            return await _ensure(self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required("spaces", default=user_input.get("spaces", "[]")): str,
                        vol.Required("links", default=user_input.get("links", "[]")): str,
                    }
                ),
                errors={"base": (space_errors or link_errors)[0]},
            ))
        return await _ensure(
            self.async_create_entry(
                title=self.config_entry.title,
                data={CONF_SPACES: spaces, CONF_LINKS: links},
            )
        )


def _parse_spaces(payload: str) -> list[dict[str, Any]]:
    stripped = payload.strip()
    if not stripped:
        return []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = _coerce_space_names(payload)
    if not isinstance(data, list):
        raise ValueError
    spaces: list[dict[str, Any]] = []
    for raw in data:
        validated = SPACE_FIELD(raw)
        space_id = validated.get("id") or slugify(validated["name"])
        spaces.append({**validated, "id": space_id})
    ensure_unique_ids(space["id"] for space in spaces)
    return spaces


def _coerce_space_names(payload: str) -> list[dict[str, Any]]:
    names: list[str] = []
    for line in payload.splitlines():
        parts = [part.strip() for part in line.split(",")]
        for name in parts:
            if name:
                names.append(name)
    if not names:
        raise ValueError
    return [{"name": name} for name in names]


def _parse_links(payload: str) -> list[dict[str, Any]]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError
    links: list[dict[str, Any]] = []
    for raw in data:
        validated = LINK_FIELD(raw)
        link_id = validated.get("id") or slugify(
            f"{validated['from_space']}_{validated['to_space']}_{validated['name']}"
        )
        links.append({**validated, "id": link_id})
    ensure_unique_ids(link["id"] for link in links)
    return links


def _validate_spaces(spaces: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids = {space["id"] for space in spaces}
    if len(ids) != len(spaces):
        errors.append("duplicate_id")
    return errors


def _validate_links(spaces: list[dict[str, Any]], links: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    space_ids = {space["id"] for space in spaces}
    for link in links:
        if link["from_space"] not in space_ids or link["to_space"] not in space_ids:
            errors.append("missing_space")
            break
    return errors


async def _ensure(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
