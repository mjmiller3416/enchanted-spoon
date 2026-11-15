"""app/dtos/oauth_dtos.py

DTOs for the consent page and Settings' connected-apps card. The token,
registration and discovery endpoints speak raw RFC JSON/form bodies instead
(app/api/oauth.py), so their error shapes match the RFCs exactly.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AuthorizeParamsDTO(BaseModel):
    """The authorization request's query parameters, as the consent page received them."""

    response_type: Optional[str] = Field(None, max_length=32)
    client_id: Optional[str] = Field(None, max_length=64)
    redirect_uri: Optional[str] = Field(None, max_length=2048)
    code_challenge: Optional[str] = Field(None, max_length=128)
    code_challenge_method: Optional[str] = Field(None, max_length=16)
    state: Optional[str] = Field(None, max_length=2048)
    scope: Optional[str] = Field(None, max_length=1024)
    resource: Optional[str] = Field(None, max_length=2048)


class AuthorizeDecisionDTO(AuthorizeParamsDTO):
    """What the consent page sends when the person presses Allow or Cancel."""

    decision: Literal["allow", "deny"]


class AuthorizeCheckDTO(BaseModel):
    """How the consent page should treat a request.

    ``ok``: show consent for ``client_name``, worded for ``scope`` (``mcp``:
    everything you can do; ``alexa``: add to and read the shopping list).
    ``redirect``: the request is malformed but safe to send back; go to
    ``redirect_to``. ``error``: show ``message`` and don't redirect anywhere.
    """

    status: Literal["ok", "redirect", "error"]
    client_name: Optional[str] = None
    scope: Optional[str] = None
    redirect_to: Optional[str] = None
    message: Optional[str] = None


class AuthorizeResultDTO(BaseModel):
    """Where the consent page sends the browser next (the client's redirect URI with code or error)."""

    redirect_to: str


class ConnectionDTO(BaseModel):
    """One connected app, for Settings."""

    client_name: str
    connected_at: datetime
    scope: str = "mcp"  # "mcp": everything; "alexa": add to and read the shopping list


class ConnectionsDTO(BaseModel):
    """The signed-in person's connected apps."""

    connections: List[ConnectionDTO]


class DisconnectResultDTO(BaseModel):
    """How many tokens a disconnect revoked."""

    revoked: int
