"""DTOs for household sharing."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class HouseholdCreateDTO(BaseModel):
    """Create a household the caller will own."""

    name: str = Field(..., min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Give the household a name.")
        return cleaned


class HouseholdUpdateDTO(BaseModel):
    """Rename a household."""

    name: str = Field(..., min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Give the household a name.")
        return cleaned


class HouseholdInviteCreateDTO(BaseModel):
    """Invite by link. Email is optional and only restricts who may redeem it."""

    email: Optional[str] = Field(None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return cleaned


class HouseholdJoinDTO(BaseModel):
    """Redeem an invite code."""

    code: str = Field(..., min_length=4, max_length=64)


class HouseholdTransferDTO(BaseModel):
    """Hand ownership to an existing member."""

    user_id: int


class HouseholdMemberDTO(BaseModel):
    user_id: int
    name: Optional[str] = None
    email: str
    role: str
    joined_at: datetime


class HouseholdInviteDTO(BaseModel):
    id: int
    code: str
    email: Optional[str] = None
    expires_at: datetime
    created_at: datetime


class HouseholdDTO(BaseModel):
    """The caller's household, including members and (for the owner) open invites."""

    id: int
    name: str
    role: str
    owner_user_id: int
    # True when the owner's subscription, grant, or admin flag covers members.
    pro_covers_members: bool
    members: List[HouseholdMemberDTO]
    invites: List[HouseholdInviteDTO] = []


class HouseholdStateDTO(BaseModel):
    """GET /api/household — ``household`` is null when the user has none."""

    household: Optional[HouseholdDTO] = None
