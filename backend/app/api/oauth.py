"""app/api/oauth.py

OAuth 2.1 authorization server for the MCP connector (ChatGPT custom
connectors), plus its discovery documents.

    GET  /.well-known/oauth-protected-resource[/api/mcp]   RFC 9728
    GET  /.well-known/oauth-authorization-server           RFC 8414
    POST /api/oauth/register                               RFC 7591 (DCR)
    GET  /api/oauth/authorize                              302 to the consent page
    GET  /api/oauth/authorize/check                        the consent page validates its query
    POST /api/oauth/authorize                              Allow/Cancel (Clerk JWT) -> redirect URL
    POST /api/oauth/token                                  authorization_code, refresh_token
    POST /api/oauth/revoke                                 RFC 7009
    GET/DELETE /api/oauth/connections                      Settings: list / disconnect (Clerk JWT)

The consent page is the frontend's ``/oauth/authorize`` (behind Clerk's
middleware, so a signed-out person signs in first and comes back with the
query intact). It calls ``POST /api/oauth/authorize`` with the person's Clerk
JWT in the Authorization header; a header a third-party page can't set is
what protects that POST from cross-site forgery.

Every authorize redirect, success or error, carries ``iss`` (RFC 9207).
With ``MCP_ENABLED=false`` everything here answers 404.
"""

import base64
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.mcp_config import (
    ALEXA_SCOPE,
    MCP_PATH,
    MCP_SCOPE,
    authorization_page_url,
    mcp_enabled,
    public_origin,
    resource_url,
)
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.dtos.oauth_dtos import (
    AuthorizeCheckDTO,
    AuthorizeDecisionDTO,
    AuthorizeParamsDTO,
    AuthorizeResultDTO,
    ConnectionDTO,
    ConnectionsDTO,
    DisconnectResultDTO,
)
from app.models.user import User
from app.services.oauth_service import (
    AUTH_METHODS,
    AuthorizeRedirectError,
    AuthorizeRequestError,
    OAuthError,
    OAuthService,
)

logger = logging.getLogger(__name__)

well_known_router = APIRouter()
router = APIRouter()

NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def require_mcp_enabled() -> None:
    """404 everything when the kill switch (``MCP_ENABLED=false``) is off."""
    if not mcp_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


# ── Discovery ───────────────────────────────────────────────────────────────
def protected_resource_metadata() -> Dict[str, Any]:
    """RFC 9728 metadata for ``/api/mcp``."""
    return {
        "resource": resource_url(),
        "authorization_servers": [public_origin()],
        "scopes_supported": [MCP_SCOPE],
        "bearer_methods_supported": ["header"],
        "resource_name": "Enchanted Spoon",
    }


def authorization_server_metadata() -> Dict[str, Any]:
    """RFC 8414 metadata. No openid-configuration on purpose (ChatGPT would ask for every OIDC scope)."""
    origin = public_origin()
    return {
        "issuer": origin,
        "authorization_endpoint": authorization_page_url(),
        "token_endpoint": f"{origin}/api/oauth/token",
        "registration_endpoint": f"{origin}/api/oauth/register",
        "revocation_endpoint": f"{origin}/api/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": list(AUTH_METHODS),
        "revocation_endpoint_auth_methods_supported": list(AUTH_METHODS),
        "scopes_supported": [MCP_SCOPE, ALEXA_SCOPE],
        "authorization_response_iss_parameter_supported": True,
    }


@well_known_router.get("/.well-known/oauth-protected-resource", include_in_schema=False)
@well_known_router.get(f"/.well-known/oauth-protected-resource{MCP_PATH}", include_in_schema=False)
def get_protected_resource_metadata(_: None = Depends(require_mcp_enabled)) -> JSONResponse:
    """Where to get tokens for the MCP server."""
    return JSONResponse(protected_resource_metadata())


@well_known_router.get("/.well-known/oauth-authorization-server", include_in_schema=False)
def get_authorization_server_metadata(_: None = Depends(require_mcp_enabled)) -> JSONResponse:
    """The authorization server's endpoints and capabilities."""
    return JSONResponse(authorization_server_metadata())


# ── Helpers ─────────────────────────────────────────────────────────────────
def with_query(uri: str, params: Dict[str, Optional[str]]) -> str:
    """Add parameters to a redirect URI, keeping any query it already has."""
    parts = urlsplit(uri)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend((k, v) for k, v in params.items() if v is not None)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def error_redirect(exc: AuthorizeRedirectError) -> str:
    """The client's redirect URI carrying an authorize error, its state and our issuer."""
    return with_query(
        exc.redirect_uri,
        {"error": exc.error, "error_description": exc.description, "state": exc.state, "iss": public_origin()},
    )


def oauth_error_response(exc: OAuthError) -> JSONResponse:
    """RFC 6749 section 5.2 error JSON."""
    headers = dict(NO_STORE)
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = 'Basic realm="enchanted-spoon"'
    return JSONResponse(
        {"error": exc.error, "error_description": exc.description}, status_code=exc.status_code, headers=headers
    )


def _validate(service: OAuthService, params: AuthorizeParamsDTO):
    return service.validate_authorize_request(
        response_type=params.response_type,
        client_id=params.client_id,
        redirect_uri=params.redirect_uri,
        code_challenge=params.code_challenge,
        code_challenge_method=params.code_challenge_method,
        state=params.state,
        scope=params.scope,
        resource=params.resource,
    )


async def _form(request: Request) -> Dict[str, str]:
    """A form-encoded body as a plain dict (the token and revocation endpoints)."""
    form = await request.form()
    return {k: v for k, v in form.items() if isinstance(v, str)}


def _client_credentials(request: Request, form: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
    """client_id and client_secret from HTTP Basic (RFC 6749 2.3.1) or the form body.

    Raises:
        OAuthError: A malformed Basic header (``invalid_client``).
    """
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
            raw_id, _, raw_secret = decoded.partition(":")
        except (ValueError, UnicodeDecodeError):
            raise OAuthError("invalid_client", "Malformed Basic authorization header.", 401)
        return unquote(raw_id), unquote(raw_secret)
    return form.get("client_id"), form.get("client_secret")


# ── Registration ────────────────────────────────────────────────────────────
@router.post("/register", include_in_schema=False)
@limiter.limit("30/hour")
async def register_client(
    request: Request,
    session: Session = Depends(get_session),
    _: None = Depends(require_mcp_enabled),
) -> JSONResponse:
    """Dynamic client registration (RFC 7591). ChatGPT registers itself here."""
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        return JSONResponse(
            {"error": "invalid_client_metadata", "error_description": "Expected a JSON object."},
            status_code=400,
            headers=NO_STORE,
        )
    service = OAuthService(session)
    try:
        registered = await run_in_threadpool(
            service.register_client,
            body.get("redirect_uris"),
            body.get("client_name"),
            body.get("token_endpoint_auth_method"),
            body.get("grant_types"),
        )
    except OAuthError as exc:
        return oauth_error_response(exc)
    client = registered.client
    payload: Dict[str, Any] = {
        "client_id": client.client_id,
        "client_id_issued_at": int(client.created_at.timestamp()),
        "redirect_uris": body.get("redirect_uris"),
        "token_endpoint_auth_method": client.token_endpoint_auth_method,
        "grant_types": json.loads(client.grant_types),
        "response_types": ["code"],
        "scope": MCP_SCOPE,
    }
    if client.client_name:
        payload["client_name"] = client.client_name
    if registered.client_secret:
        payload["client_secret"] = registered.client_secret
        payload["client_secret_expires_at"] = 0
    return JSONResponse(payload, status_code=201, headers=NO_STORE)


# ── Authorization ───────────────────────────────────────────────────────────
@router.get("/authorize", include_in_schema=False)
def authorize_redirect(request: Request, _: None = Depends(require_mcp_enabled)) -> RedirectResponse:
    """Send a browser that lands here to the consent page, query intact."""
    target = authorization_page_url()
    query = request.url.query
    return RedirectResponse(f"{target}?{query}" if query else target, status_code=302)


@router.get("/authorize/check", response_model=AuthorizeCheckDTO)
def check_authorize_request(
    params: AuthorizeParamsDTO = Depends(),
    session: Session = Depends(get_session),
    _: None = Depends(require_mcp_enabled),
) -> AuthorizeCheckDTO:
    """Tell the consent page whether to show consent, redirect with an error, or show an error."""
    service = OAuthService(session)
    try:
        request = _validate(service, params)
    except AuthorizeRequestError as exc:
        return AuthorizeCheckDTO(status="error", message=str(exc))
    except AuthorizeRedirectError as exc:
        return AuthorizeCheckDTO(status="redirect", redirect_to=error_redirect(exc))
    return AuthorizeCheckDTO(status="ok", client_name=request.client_name, scope=request.scope)


@router.post("/authorize", response_model=AuthorizeResultDTO)
def decide_authorize_request(
    body: AuthorizeDecisionDTO,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _: None = Depends(require_mcp_enabled),
) -> AuthorizeResultDTO:
    """Allow or Cancel on the consent page, as the signed-in person. Returns where to send the browser."""
    service = OAuthService(session)
    try:
        request = _validate(service, body)
    except AuthorizeRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AuthorizeRedirectError as exc:
        return AuthorizeResultDTO(redirect_to=error_redirect(exc))
    if body.decision == "deny":
        return AuthorizeResultDTO(
            redirect_to=with_query(
                request.redirect_uri,
                {
                    "error": "access_denied",
                    "error_description": "The user declined.",
                    "state": request.state,
                    "iss": public_origin(),
                },
            )
        )
    code = service.issue_code(request, current_user.id)
    return AuthorizeResultDTO(
        redirect_to=with_query(request.redirect_uri, {"code": code, "state": request.state, "iss": public_origin()})
    )


# ── Tokens ──────────────────────────────────────────────────────────────────
@router.post("/token", include_in_schema=False)
async def token(
    request: Request,
    session: Session = Depends(get_session),
    _: None = Depends(require_mcp_enabled),
) -> JSONResponse:
    """The token endpoint: ``authorization_code`` and ``refresh_token`` grants."""
    service = OAuthService(session)
    try:
        form = await _form(request)
        client_id, client_secret = _client_credentials(request, form)
        client = await run_in_threadpool(service.authenticate_client, client_id, client_secret)
        grant_type = form.get("grant_type")
        if grant_type == "authorization_code":
            pair = await run_in_threadpool(
                lambda: service.exchange_code(
                    client,
                    code=form.get("code"),
                    redirect_uri=form.get("redirect_uri"),
                    code_verifier=form.get("code_verifier"),
                    resource=form.get("resource"),
                )
            )
        elif grant_type == "refresh_token":
            pair = await run_in_threadpool(
                lambda: service.refresh(client, refresh_token=form.get("refresh_token"), resource=form.get("resource"))
            )
        else:
            raise OAuthError("unsupported_grant_type", "grant_type must be authorization_code or refresh_token.")
    except OAuthError as exc:
        return oauth_error_response(exc)
    return JSONResponse(
        {
            "access_token": pair.access_token,
            "token_type": "Bearer",
            "expires_in": pair.expires_in,
            "refresh_token": pair.refresh_token,
            "scope": pair.scope,
        },
        headers=NO_STORE,
    )


@router.post("/revoke", include_in_schema=False)
async def revoke(
    request: Request,
    session: Session = Depends(get_session),
    _: None = Depends(require_mcp_enabled),
) -> JSONResponse:
    """Token revocation (RFC 7009): ends the connection the token belongs to."""
    service = OAuthService(session)
    try:
        form = await _form(request)
        client_id, client_secret = _client_credentials(request, form)
        client = await run_in_threadpool(service.authenticate_client, client_id, client_secret)
        await run_in_threadpool(service.revoke, client, form.get("token"))
    except OAuthError as exc:
        return oauth_error_response(exc)
    return JSONResponse({}, headers=NO_STORE)


# ── Connected apps (Settings) ───────────────────────────────────────────────
@router.get("/connections", response_model=ConnectionsDTO)
def list_connections(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectionsDTO:
    """The apps (ChatGPT) the signed-in person has connected."""
    connections = OAuthService(session).list_connections(current_user.id)
    return ConnectionsDTO(
        connections=[
            ConnectionDTO(client_name=c.client_name, connected_at=c.connected_at, scope=c.scope) for c in connections
        ]
    )


@router.delete("/connections", response_model=DisconnectResultDTO)
def disconnect_all(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DisconnectResultDTO:
    """Disconnect every connected app: all of the person's tokens stop working at once."""
    return DisconnectResultDTO(revoked=OAuthService(session).disconnect_all(current_user.id))
