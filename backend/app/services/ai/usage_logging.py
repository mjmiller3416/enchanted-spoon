"""Log Gemini usage_metadata without storing prompt text."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("app.ai.usage")


def _read(meta: Any, name: str) -> Optional[int]:
    if meta is None:
        return None
    if isinstance(meta, dict):
        value = meta.get(name)
    else:
        value = getattr(meta, name, None)
    return value if isinstance(value, int) else None


def log_usage_metadata(feature: str, model: str, response: Any) -> None:
    """Record prompt, candidate, thought, and cached token counts for one call."""
    meta = getattr(response, "usage_metadata", None)
    if meta is None and isinstance(response, dict):
        meta = response.get("usage_metadata")
    logger.info(
        "gemini_usage feature=%s model=%s prompt_tokens=%s candidate_tokens=%s "
        "thought_tokens=%s cached_tokens=%s",
        feature,
        model,
        _read(meta, "prompt_token_count"),
        _read(meta, "candidates_token_count"),
        _read(meta, "thoughts_token_count"),
        _read(meta, "cached_content_token_count"),
    )
