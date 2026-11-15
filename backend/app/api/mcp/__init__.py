"""app/api/mcp

The MCP server at ``/api/mcp`` for ChatGPT custom connectors (Streamable
HTTP, stateless, JSON responses).

Every request needs ``Authorization: Bearer <access token>`` issued by the
OAuth server (app/api/oauth.py); the call then acts as the person who
consented. Without a valid token the answer is 401 with a
``WWW-Authenticate`` header pointing at the protected-resource metadata,
which is how ChatGPT discovers where to sign in. ``MCP_ENABLED=false``
turns the endpoint into a 404.

Modules: ``server`` (JSON-RPC), ``tools`` (the catalogue), ``dispatch``
(calls the app's own routes in process).
"""

import json
import logging
import re
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.api.mcp import server
from app.api.mcp.tools import ToolContext
from app.core.mcp_config import MCP_PATH, MCP_SCOPE, mcp_enabled, public_origin
from app.database.db import get_session
from app.services.oauth_service import OAuthService

logger = logging.getLogger(__name__)

router = APIRouter()

BEARER = re.compile(r"^Bearer\s+(\S+)$", re.IGNORECASE)


def unauthorized(error: Optional[str] = None) -> JSONResponse:
    """401 that tells the client where to find the authorization server (RFC 9728 section 5.1)."""
    header = f'Bearer resource_metadata="{public_origin()}/.well-known/oauth-protected-resource", scope="{MCP_SCOPE}"'
    if error:
        header += f', error="{error}"'
    body = {"error": error or "unauthorized", "error_description": "Sign in to Enchanted Spoon to use this connector."}
    return JSONResponse(body, status_code=401, headers={"WWW-Authenticate": header})


@router.api_route(MCP_PATH, methods=["GET", "POST", "DELETE"], include_in_schema=False)
async def mcp_endpoint(request: Request, session: Session = Depends(get_session)) -> Response:
    """Check the access token, then answer the JSON-RPC message(s) in the body."""
    if not mcp_enabled():
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    authorization = request.headers.get("authorization")
    match = BEARER.match(authorization or "")
    if match is None:
        return unauthorized()
    user_id = await run_in_threadpool(OAuthService(session).user_for_access_token, match.group(1))
    session.close()  # tools use their own sessions; don't hold this connection while they run
    if user_id is None:
        return unauthorized("invalid_token")
    if request.method != "POST":
        # No server-initiated stream (GET) and no sessions to end (DELETE) on a stateless server.
        return JSONResponse({"detail": "Method Not Allowed"}, status_code=405, headers={"Allow": "POST"})

    try:
        payload: Any = json.loads(await request.body())
    except ValueError:
        return JSONResponse(server._error(None, server.PARSE_ERROR, "Invalid JSON."), status_code=400)

    ctx = ToolContext(user_id=user_id, authorization=authorization)
    if isinstance(payload, list):
        if not payload:
            return JSONResponse(server._error(None, server.INVALID_REQUEST, "Empty batch."), status_code=400)
        replies: List[Any] = [r for r in [await server.handle_message(m, ctx) for m in payload] if r is not None]
        return JSONResponse(replies) if replies else Response(status_code=202)
    reply = await server.handle_message(payload, ctx)
    if reply is None:
        return Response(status_code=202)
    return JSONResponse(reply)
