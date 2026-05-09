"""Shared response schemas and timezone-rendering helpers.

The OSS server stores timestamps in UTC (``DateTime(timezone=True)`` columns,
``_utcnow`` defaults, ``datetime.now(timezone.utc)`` for memory payloads) and
renders them in **Asia/Shanghai** on the JSON wire format. The DB layer is not
touched — only the serialization layer changes. See
``server/docker-compose.yaml`` for the matching container ``TZ`` setting.
"""

from datetime import datetime
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from pydantic import BaseModel

# Single source of truth for the user-facing timezone. Imported by routers and
# main.py so any future change (e.g., env-driven TZ) flips all responses at once.
SHANGHAI = ZoneInfo("Asia/Shanghai")

_TIMESTAMP_KEYS = ("created_at", "updated_at", "feedback_updated_at", "last_login_at")


def to_shanghai_iso(value: Union[datetime, str, None]) -> Optional[str]:
    """Render a UTC datetime / ISO string as an Asia/Shanghai ISO string.

    Accepts:
      - ``datetime`` instances (naive treated as UTC, aware converted in place)
      - ISO-8601 strings (``"...+00:00"`` or ``"...Z"``)
      - ``None`` (passes through)

    Returns the ISO-format string with a ``+08:00`` offset, or ``None``.

    This is the single conversion function used by both Pydantic
    ``field_serializer`` hooks and the ``localize_response_timestamps`` walker
    that handles raw dicts returned by the underlying ``mem0`` SDK.
    """
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            # Not a parseable timestamp — leave it untouched so we don't mangle
            # arbitrary strings that happen to share a key name.
            return str(value)

    # Naive datetimes are assumed to be UTC (matches ``_utcnow`` and the SDK's
    # ``datetime.now(timezone.utc).isoformat()`` writes).
    if dt.tzinfo is None:
        from datetime import timezone as _tz

        dt = dt.replace(tzinfo=_tz.utc)

    return dt.astimezone(SHANGHAI).isoformat()


def localize_response_timestamps(obj: Any) -> Any:
    """Recursively rewrite ``created_at``/``updated_at``/``feedback_updated_at``
    fields in any nested dict / list response from the SDK to Asia/Shanghai.

    Used by the memory endpoints (``/v3/memories/...``) which return raw dicts
    straight from the ``mem0`` SDK rather than a Pydantic model. Pydantic-model
    responses (UserResponse, KeyListItem, Entity, RequestLogItem) get the same
    behavior via ``field_serializer`` hooks on the model itself.
    """
    if isinstance(obj, dict):
        return {
            k: (to_shanghai_iso(v) if k in _TIMESTAMP_KEYS else localize_response_timestamps(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [localize_response_timestamps(item) for item in obj]
    return obj


class MessageResponse(BaseModel):
    message: str
