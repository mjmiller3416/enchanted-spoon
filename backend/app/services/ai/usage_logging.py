"""Log Gemini usage_metadata without storing prompt text."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.request_context import current_request_id, current_user_id

logger = logging.getLogger("app.ai.usage")


def _read(meta: Any, name: str) -> Optional[int]:
    if meta is None:
        return None
    if isinstance(meta, dict):
        value = meta.get(name)
    else:
        value = getattr(meta, name, None)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _count(value: int) -> int:
    """A non-negative count. Missing or invalid values are zero."""
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value if value > 0 else 0


def _user_id(explicit: Optional[int]) -> str:
    value = explicit if explicit is not None else current_user_id()
    if isinstance(value, bool) or not isinstance(value, int):
        return "none"
    return str(value)


def _request_id() -> str:
    value = current_request_id()
    if isinstance(value, str) and value:
        return value
    return "none"


def log_usage_metadata(
    feature: str,
    model: str,
    response: Any,
    *,
    user_id: Optional[int] = None,
    photo_count: int = 0,
    image_count: int = 0,
    fallback: bool = False,
) -> None:
    """Record token counts and call context for one provider call.

    ``photo_count`` is the number of input photos. ``image_count`` is the
    number of images this call generated. Both are 0 when there are none.
    ``fallback`` is true when a fallback model or fallback path was used.
    The request id and user id come from the request context unless
    ``user_id`` is passed. Prompt text, emails, and secrets are not logged.
    """
    meta = getattr(response, "usage_metadata", None)
    if meta is None and isinstance(response, dict):
        meta = response.get("usage_metadata")
    logger.info(
        "gemini_usage feature=%s model=%s prompt_tokens=%s candidate_tokens=%s "
        "thought_tokens=%s cached_tokens=%s user_id=%s photo_count=%s "
        "image_count=%s fallback=%s request_id=%s",
        feature,
        model,
        _read(meta, "prompt_token_count"),
        _read(meta, "candidates_token_count"),
        _read(meta, "thoughts_token_count"),
        _read(meta, "cached_content_token_count"),
        _user_id(user_id),
        _count(photo_count),
        _count(image_count),
        "true" if fallback else "false",
        _request_id(),
    )
