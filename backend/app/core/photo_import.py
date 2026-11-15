"""Feature flag for photo-to-recipe import.

Off unless ``PHOTO_IMPORT_ENABLED`` is a truthy value. The route stays
registered, returns 404 until the flag is on, and does not reserve an import.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def photo_import_enabled() -> bool:
    """True only when the operator has explicitly turned photo import on."""
    raw = os.getenv("PHOTO_IMPORT_ENABLED", "")
    return raw.strip().lower() in _TRUTHY
