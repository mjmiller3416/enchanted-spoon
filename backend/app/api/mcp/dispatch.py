"""app/api/mcp/dispatch.py

How an MCP tool reaches the app: it sends an HTTP request to the app's own
API routes, in process (no network hop), and gets back what a person
clicking in the app would. Going through the routes keeps a tool and the app
exactly alike: same validation, same read-only and usage-limit checks, same
services and side effects.

The requests go to an internal copy of the API (``internal_app``) that is
never served on a port. It mounts the public ``api_router`` unchanged and
shares the public app's exception handlers and dependency overrides (so tests
reach their own database). The one difference: ``get_current_user`` is
replaced by ``_mcp_user``, which loads the account the MCP request's access
token belongs to (``x-mcp-user-id``, set only by this module; nothing outside
the process can reach this app to send it).
"""

from __future__ import annotations

import logging
from collections import ChainMap
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.observability import set_user as set_error_reporting_user
from app.core.request_context import bind_usage_user_id
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.models.user import User
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

USER_HEADER = "x-mcp-user-id"
INTERNAL_BASE_URL = "http://enchanted-spoon.internal"

_internal: Optional[FastAPI] = None


async def _mcp_user(request: Request, session: Session = Depends(get_session)) -> User:
    """Stands in for ``get_current_user`` on the internal app: the MCP token's account."""
    raw = request.headers.get(USER_HEADER)
    user = UserService(session).get_by_id(int(raw)) if raw and raw.isdigit() else None
    if user is None:
        raise HTTPException(status_code=401, detail="This connection's Enchanted Spoon account no longer exists.")
    UserService(session).touch_last_active(user)
    set_error_reporting_user(user.id)
    bind_usage_user_id(user.id)
    return user


def internal_app() -> FastAPI:
    """The internal API app tools call (built once, on first use)."""
    global _internal
    if _internal is None:
        from app.main import app as public  # late import: main imports the router that imports this
        from app.router import api_router

        internal = FastAPI(openapi_url="/openapi.json", docs_url=None, redoc_url=None)
        internal.state.limiter = limiter
        for exc_class, handler in public.exception_handlers.items():
            internal.add_exception_handler(exc_class, handler)
        internal.include_router(api_router)
        internal.dependency_overrides = ChainMap(  # type: ignore[assignment]
            {get_current_user: _mcp_user}, public.dependency_overrides
        )
        _internal = internal
    return _internal


class ToolCallError(Exception):
    """The app refused a tool's request. The message is what the person would have been told."""


def error_message(status: int, body: Any) -> str:
    """The app's refusal as one plain sentence the model can act on."""
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):
        detail = detail.get("message") or detail.get("error")
    if isinstance(detail, list):
        # FastAPI's 422: one entry per bad field
        parts = []
        for item in detail:
            where = ".".join(str(p) for p in item.get("loc", []) if p not in ("body", "query", "path"))
            msg = str(item.get("msg", "")).removeprefix("Value error, ")
            parts.append(f"{where}: {msg}" if where else msg)
        detail = "Invalid input — " + "; ".join(parts)
    if not detail and isinstance(body, dict):
        detail = body.get("error") if isinstance(body.get("error"), str) else None
    if status == 404 and not detail:
        detail = "Not found."
    if status >= 500:
        return f"Enchanted Spoon hit a server error (HTTP {status}). Try again in a moment."
    return f"{detail or 'The request was refused'} (HTTP {status})"


async def call(
    user_id: int,
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Any = None,
    form: Optional[Dict[str, str]] = None,
    authorization: Optional[str] = None,
) -> Any:
    """Send one request to the internal API as ``user_id`` and return its JSON (None if empty).

    Args:
        user_id: The account the MCP token belongs to.
        method: HTTP method.
        path: Path with its parameters filled in.
        params: Query parameters; None values are dropped, lists repeat the key.
        json_body: JSON body, sent when not None.
        form: Form fields (application/x-www-form-urlencoded), for the one
            form route a tool uses (the base64 image upload).
        authorization: The MCP request's Authorization header, passed on only so
            per-caller rate limits bucket each connection separately.

    Raises:
        ToolCallError: The API answered 4xx/5xx.
    """
    headers = {USER_HEADER: str(user_id)}
    if authorization:
        headers["authorization"] = authorization
    query = {k: v for k, v in (params or {}).items() if v is not None}
    transport = httpx.ASGITransport(app=internal_app())
    async with httpx.AsyncClient(transport=transport, base_url=INTERNAL_BASE_URL, timeout=None) as client:
        response = await client.request(
            method, path, params=query or None, json=json_body, data=form, headers=headers
        )
    logger.info("mcp tool %s %s -> %s", method, path, response.status_code)
    try:
        body = response.json() if response.content else None
    except ValueError:
        body = response.text
    if response.status_code >= 400:
        raise ToolCallError(error_message(response.status_code, body))
    return body
