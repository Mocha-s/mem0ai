import json
import logging
import threading
from copy import deepcopy
from typing import Any, Callable, Dict

from mem0 import Memory

_state_lock = threading.RLock()
_current_config: Dict[str, Any] = {}
_memory_instance: Memory | None = None
_session_factory: Callable | None = None

# Fields that live on the Project entity, not in the global Settings.config_overrides.
# Both /configure POST and /project PATCH must agree on this list — see
# `assert_no_project_fields_in_config()` for the validator.
PROJECT_FIELDS = (
    "custom_instructions",
    "custom_categories",
    "retrieval_criteria",
    "multilingual",
    "decay",
)


class ProjectFieldsRejected(ValueError):
    """Raised when a caller submits project-scoped fields to /configure."""


def assert_no_project_fields_in_config(config: Dict[str, Any]) -> None:
    """Reject project-scoped fields submitted to ``POST /configure``.

    These fields belong on the Project entity (`PATCH /project`) — leaving the
    /configure path silently accepting them caused ambiguous merge ordering and
    is now a hard error.
    """
    invalid = sorted(field for field in PROJECT_FIELDS if field in config)
    if invalid:
        raise ProjectFieldsRejected(
            "Fields {fields} are project-scoped. Use PATCH /project to update them.".format(
                fields=invalid
            )
        )


def set_session_factory(factory: Callable) -> None:
    global _session_factory
    _session_factory = factory


def _load_overrides() -> Dict[str, Any]:
    try:
        if _session_factory is None:
            return {}
        from models import Settings

        session = _session_factory()
        try:
            row = session.get(Settings, "config_overrides")
            if row is None:
                return {}
            return json.loads(row.value)
        finally:
            session.close()
    except Exception:
        return {}


def _load_project() -> Dict[str, Any]:
    """Load the default project's project-scoped fields as a flat dict.

    Returns an empty dict if the projects table doesn't exist yet (tests not
    using the DB) or when no default row is present. Missing/None fields are
    simply omitted so they don't override defaults.
    """
    try:
        if _session_factory is None:
            return {}
        from sqlalchemy import select

        from models import Project

        session = _session_factory()
        try:
            row = session.execute(
                select(Project).where(Project.is_default.is_(True))
            ).scalar_one_or_none()
            if row is None:
                return {}
            return _project_row_to_config(row)
        finally:
            session.close()
    except Exception:
        return {}


def _project_row_to_config(row: Any) -> Dict[str, Any]:
    """Convert a Project SQLAlchemy row into the dict shape that MemoryConfig accepts."""
    config: Dict[str, Any] = {}
    if row.custom_instructions is not None:
        config["custom_instructions"] = row.custom_instructions
    if row.custom_categories is not None:
        config["custom_categories"] = _maybe_json_loads(row.custom_categories)
    if row.retrieval_criteria is not None:
        config["retrieval_criteria"] = _maybe_json_loads(row.retrieval_criteria)
    config["multilingual"] = bool(row.multilingual)
    config["decay"] = bool(row.decay)
    return config


def _maybe_json_loads(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _save_overrides(overrides: Dict[str, Any]) -> None:
    try:
        if _session_factory is None:
            return
        from models import Settings
        from sqlalchemy.dialects.postgresql import insert

        session = _session_factory()
        try:
            serialized = json.dumps(overrides)
            stmt = (
                insert(Settings)
                .values(key="config_overrides", value=serialized)
                .on_conflict_do_update(
                    index_elements=[Settings.key],
                    set_={"value": serialized},
                )
            )
            session.execute(stmt)
            session.commit()
        finally:
            session.close()
    except Exception:
        logging.warning("Failed to persist config overrides to database", exc_info=True)


def _merge_config(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)

    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = value

    return merged


def initialize_state(default_config: Dict[str, Any]) -> None:
    global _current_config, _memory_instance
    with _state_lock:
        _current_config = deepcopy(default_config)
        overrides = _load_overrides()
        if overrides:
            _current_config = _merge_config(_current_config, overrides)
        # Project-scoped fields override anything from config_overrides — they have
        # a typed schema and a real PATCH endpoint, while config_overrides is the
        # legacy global blob.
        project_fields = _load_project()
        if project_fields:
            _current_config = _merge_config(_current_config, project_fields)
        _memory_instance = Memory.from_config(_current_config)


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    global _current_config, _memory_instance
    with _state_lock:
        assert_no_project_fields_in_config(updates)
        next_config = _merge_config(_current_config, updates)
        _current_config = next_config
        _memory_instance = Memory.from_config(next_config)
        overrides = _load_overrides()
        overrides = _merge_config(overrides, updates)
        _save_overrides(overrides)
        return deepcopy(_current_config)


def update_project(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Persist project-scoped field updates and rebuild the Memory instance.

    Mirrors :func:`update_config`: writes to the projects table, re-loads the
    full active config (DEFAULT + overrides + project fields), and constructs a
    fresh Memory so search-time fields (criteria, decay, multilingual) take
    effect immediately. Returns the full active config.
    """
    global _current_config, _memory_instance
    if not updates:
        raise ValueError("update_project requires at least one field.")
    invalid = sorted(set(updates) - set(PROJECT_FIELDS))
    if invalid:
        raise ValueError(f"Unknown project fields: {invalid}")

    with _state_lock:
        if _session_factory is None:
            raise RuntimeError("Session factory not configured; cannot update project.")

        from sqlalchemy import select

        from models import Project

        session = _session_factory()
        try:
            row = session.execute(
                select(Project).where(Project.is_default.is_(True))
            ).scalar_one_or_none()
            if row is None:
                raise RuntimeError(
                    "Default project row missing — alembic 007 should have seeded it."
                )
            for field, value in updates.items():
                setattr(row, field, value)
            session.commit()
            session.refresh(row)
            project_fields = _project_row_to_config(row)
        finally:
            session.close()

        _current_config = _merge_config(_current_config, project_fields)
        _memory_instance = Memory.from_config(_current_config)
        return deepcopy(_current_config)


def get_project() -> Dict[str, Any]:
    """Return the default project's fields (or empty dict if not initialized)."""
    return _load_project()


def get_current_config() -> Dict[str, Any]:
    with _state_lock:
        return deepcopy(_current_config)


def get_memory_instance() -> Memory:
    with _state_lock:
        if _memory_instance is None:
            raise RuntimeError("Mem0 runtime has not been initialized.")
        return _memory_instance
