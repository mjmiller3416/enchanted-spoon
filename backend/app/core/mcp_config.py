"""app/core/mcp_config.py

Settings for the MCP server (``/api/mcp``) and the OAuth 2.1 authorization
server that ChatGPT custom connectors use to reach it.

The public origin is the URL people paste into ChatGPT, minus ``/api/mcp``.
It comes from configuration, never from the request's Host header:
``MCP_PUBLIC_URL`` when set, else ``FRONTEND_URL`` (the site's own address,
already used for Stripe redirects). In production that is the frontend's
domain, which proxies ``/api/mcp``, ``/api/oauth/*`` and the two
``/.well-known/oauth-*`` documents to this backend (``frontend/next.config.ts``).
"""

import os

MCP_PATH = "/api/mcp"
MCP_SCOPE = "mcp"
# The Alexa skill's narrower grant: its token works only at /api/alexa
# (add to and read the shopping list), never at /api/mcp.
ALEXA_SCOPE = "alexa"

# Lifetimes (seconds). Refresh tokens slide: each use issues a new one with a
# fresh 90 days.
ACCESS_TOKEN_TTL = 3600
REFRESH_TOKEN_TTL = 90 * 24 * 3600
AUTHORIZATION_CODE_TTL = 600


def mcp_enabled() -> bool:
    """Whether the MCP server and its OAuth endpoints answer at all (``MCP_ENABLED``, default on).

    Set ``MCP_ENABLED=false`` to switch every connector off at once: the MCP
    endpoint, discovery documents and OAuth endpoints then answer 404 and no
    token is accepted.
    """
    return os.environ.get("MCP_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def public_origin() -> str:
    """The issuer and resource origin, with no trailing slash (e.g. ``https://enchantedspoon.app``)."""
    from .stripe_config import get_stripe_settings

    raw = os.environ.get("MCP_PUBLIC_URL", "").strip() or get_stripe_settings().frontend_url or "http://localhost:3000"
    return raw.strip().rstrip("/")


def resource_url() -> str:
    """The protected resource: the MCP endpoint's full URL."""
    return f"{public_origin()}{MCP_PATH}"


def authorization_page_url() -> str:
    """The consent page (a Next.js page behind Clerk sign-in), ``MCP_AUTHORIZE_URL`` overrides it."""
    override = os.environ.get("MCP_AUTHORIZE_URL", "").strip()
    return override or f"{public_origin()}/oauth/authorize"
