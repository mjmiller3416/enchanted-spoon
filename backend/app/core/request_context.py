"""Per-request ids for usage logs.

The middleware reads ``X-Request-ID`` (or generates one) and stores it in a
context variable so Gemini call sites can log it without a new parameter on
every service method. The same module holds the authenticated user id.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token
from typing import Optional

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"

# Printable token only. A raw header must not be able to break a log line
# or carry a prompt, email, or secret.
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar("usage_user_id", default=None)


def resolve_request_id(header_value: Optional[str]) -> str:
    """Use a safe client request id, otherwise a new uuid4."""
    if isinstance(header_value, str):
        candidate = header_value.strip()
        if _REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate
    return str(uuid.uuid4())


def current_request_id() -> Optional[str]:
    """Request id for this task, or None outside a request."""
    return request_id_var.get()


def current_user_id() -> Optional[int]:
    """Authenticated user id for this task, or None when unset."""
    return user_id_var.get()


def bind_usage_user_id(user_id: Optional[int]) -> Token:
    """Remember who this request is for. Only an int is stored."""
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        return user_id_var.set(None)
    return user_id_var.set(user_id)


class RequestIdMiddleware:
    """Attach a request id for the duration of one HTTP request.

    Pure ASGI so the context variable is visible to the endpoint. A
    ``BaseHTTPMiddleware`` runs the endpoint in a child task and would hide it.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(Headers(scope=scope).get("x-request-id"))
        request_token = request_id_var.set(request_id)
        user_token = user_id_var.set(None)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_var.reset(request_token)
            user_id_var.reset(user_token)
