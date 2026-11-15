"""app/core/alexa_config.py

Settings for the Alexa skill's endpoint (``/api/alexa``).

``ALEXA_SKILL_ID`` (comma-separated for more than one, e.g. a dev copy) is
the skill ID from the Alexa developer console. Requests naming any other
skill are refused, and with no ID set the endpoint answers 404, so the
skill is off until it is configured. Account linking uses the OAuth server
in ``app/api/oauth.py``, so ``MCP_ENABLED=false`` stops new links and token
refreshes too.
"""

import os
from typing import FrozenSet

ALEXA_PATH = "/api/alexa"


def alexa_skill_ids() -> FrozenSet[str]:
    """The skill IDs this endpoint serves (empty: the endpoint is off)."""
    raw = os.environ.get("ALEXA_SKILL_ID", "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())
