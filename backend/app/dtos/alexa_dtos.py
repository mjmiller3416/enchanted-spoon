"""app/dtos/alexa_dtos.py

Request/response bodies for linking Alexa by a spoken pairing code.
"""

from pydantic import BaseModel, Field


class AlexaLinkRequestDTO(BaseModel):
    """The six-digit code Alexa read out (spaces and dashes are ignored)."""

    code: str = Field(..., min_length=1, max_length=32)


class AlexaLinkResultDTO(BaseModel):
    """The Alexa account is now linked to the signed-in person."""

    linked: bool = True
