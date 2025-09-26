"""Constants for the Presence Graph integration."""
from __future__ import annotations

DOMAIN = "presence_graph"
PLATFORMS: list[str] = ["binary_sensor", "sensor", "switch"]
CONF_SPACES = "spaces"
CONF_LINKS = "links"
CONF_INCLUDE_IN_TOTAL = "include_in_total"
CONF_TIMEOUT = "timeout_s"
CONF_TRAVERSAL_LATENCY = "traversal_latency_s"
CONF_MOTION_ENTITIES = "motion_entities"
CONF_PRESENCE_ENTITIES = "presence_entities"
CONF_CONTACT_ENTITIES = "contact_entities"
CONF_LOCK_ENTITIES = "lock_entities"

EVENT_PRESENCE_GRAPH_UPDATE = "presence_graph_update"
ATTR_CHANGED = "changed"
ATTR_REASON = "reason"
ATTR_SOURCE_ENTITY = "source_entity_id"
ATTR_SPACE = "space"
ATTR_LINK = "link"
ATTR_SCORES = "scores"
ATTR_TOTAL_ESTIMATED = "total_estimated"
ATTR_METHOD = "method"
ATTR_SPACE_COUNTS = "space_counts"
ATTR_OCCUPIED_SPACES = "occupied_spaces"
ATTR_UPDATED_AT = "updated_at"
ATTR_LINKED_SPACES = "linked_spaces"
ATTR_LAST_EVENT = "last_event"
ATTR_SCORE = "score"
ATTR_INCLUDE_IN_TOTAL = "include_in_total"
ATTR_MOTION_ENTITIES = "motion_entities"
ATTR_PRESENCE_ENTITIES = "presence_entities"
ATTR_CONTACT = "contact"
ATTR_LOCKED = "locked"
ATTR_REASON_SENSOR = "sensor"
ATTR_REASON_LINK = "link_event"
ATTR_REASON_DECAY = "decay"
ATTR_REASON_FORCED = "manual_override"

SERVICE_RELOAD_MODEL = "reload_model"
SERVICE_SET_SPACE_INCLUDED = "set_space_included"
SERVICE_FORCE_SPACE_STATE = "force_space_state"

DATA_ENGINE = "engine"
DATA_COORDINATOR = "coordinator"
DATA_MODEL = "model"
DATA_LISTENERS = "listeners"

ENTRY_VERSION = 1

DEFAULT_TIMEOUT = 120
DEFAULT_TRAVERSAL_LATENCY = 8
DEFAULT_DECAY_THRESHOLD = 0.2
MIN_EVENT_DURATION = 0.5
LINK_EVENT_DEBOUNCE = 2.0

UPDATE_METHOD = "graph_heuristic_v1"
