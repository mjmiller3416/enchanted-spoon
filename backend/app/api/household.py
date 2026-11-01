"""Household membership, invites, and recipe sharing."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.dtos.household_dtos import (
    HouseholdCreateDTO,
    HouseholdDTO,
    HouseholdInviteCreateDTO,
    HouseholdInviteDTO,
    HouseholdJoinDTO,
    HouseholdMemberDTO,
    HouseholdStateDTO,
    HouseholdTransferDTO,
    HouseholdUpdateDTO,
)
from app.models.household import Household, HouseholdInvite
from app.models.user import User
from app.services.household.service import (
    HouseholdAlreadyMemberError,
    HouseholdError,
    HouseholdForbiddenError,
    HouseholdFullError,
    HouseholdNotFoundError,
    HouseholdService,
    InviteInvalidError,
    RecipeShareError,
)
from app.api.errors import internal_error

router = APIRouter()


def _state(session: Session, user: User, household: Household | None) -> HouseholdStateDTO:
    if household is None:
        return HouseholdStateDTO(household=None)
    return HouseholdStateDTO(household=_to_dto(session, user, household))


def _to_dto(session: Session, user: User, household: Household) -> HouseholdDTO:
    service = HouseholdService(session)
    role = service.role_for(user, household) or "member"
    owner = session.get(User, household.owner_user_id)
    members = []
    for member in service.members(household.id):
        person = session.get(User, member.user_id)
        if person is None:
            continue
        members.append(
            HouseholdMemberDTO(
                user_id=person.id,
                name=person.name,
                email=person.email,
                role=member.role,
                joined_at=member.joined_at,
            )
        )
    invites: list[HouseholdInviteDTO] = []
    if role == "owner":
        invites = [
            HouseholdInviteDTO(
                id=invite.id,
                code=invite.code,
                email=invite.email,
                expires_at=invite.expires_at,
                created_at=invite.created_at,
            )
            for invite in service.open_invites(household.id)
        ]
    return HouseholdDTO(
        id=household.id,
        name=household.name,
        role=role,
        owner_user_id=household.owner_user_id,
        pro_covers_members=bool(owner and owner.has_pro_access),
        members=members,
        invites=invites,
    )


def _http(error: HouseholdError) -> HTTPException:
    if isinstance(error, HouseholdAlreadyMemberError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, HouseholdFullError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, HouseholdForbiddenError):
        return HTTPException(status_code=403, detail=str(error))
    if isinstance(error, (HouseholdNotFoundError, InviteInvalidError)):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, RecipeShareError):
        return HTTPException(status_code=400, detail=str(error))
    return HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=HouseholdStateDTO)
def get_household(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HouseholdStateDTO:
    """The caller's household, or null when they have not joined one."""
    service = HouseholdService(session)
    return _state(session, current_user, service.get_for_user(current_user))


@router.post("", response_model=HouseholdDTO, status_code=201)
def create_household(
    body: HouseholdCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HouseholdDTO:
    """Create a household. The caller becomes the owner."""
    service = HouseholdService(session)
    try:
        household = service.create(current_user, body.name)
    except HouseholdError as error:
        raise _http(error) from error
    except Exception:
        raise internal_error("The household could not be created.")
    return _to_dto(session, current_user, household)


@router.patch("", response_model=HouseholdDTO)
def rename_household(
    body: HouseholdUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HouseholdDTO:
    """Rename the household. Owner only."""
    service = HouseholdService(session)
    try:
        household = service.rename(current_user, body.name)
    except HouseholdError as error:
        raise _http(error) from error
    return _to_dto(session, current_user, household)


@router.delete("", status_code=204)
def dissolve_household(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete the household. Owner only. Recipes stay with their creators."""
    service = HouseholdService(session)
    try:
        service.dissolve(current_user)
    except HouseholdError as error:
        raise _http(error) from error


@router.post("/invites", response_model=HouseholdInviteDTO, status_code=201)
def create_invite(
    body: HouseholdInviteCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HouseholdInviteDTO:
    """Create an invite code. Email delivery is not sent; the owner shares the link."""
    service = HouseholdService(session)
    try:
        invite = service.create_invite(current_user, body.email)
    except HouseholdError as error:
        raise _http(error) from error
    return _invite_dto(invite)


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_invite(
    invite_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke an unused invite. Owner only."""
    service = HouseholdService(session)
    try:
        service.revoke_invite(current_user, invite_id)
    except HouseholdError as error:
        raise _http(error) from error


@router.post("/join", response_model=HouseholdDTO)
@limiter.limit("10/minute")
def join_household(
    request: Request,
    body: HouseholdJoinDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HouseholdDTO:
    """Join with an invite code. Limited to slow down guessing."""
    service = HouseholdService(session)
    try:
        household = service.join(current_user, body.code)
    except HouseholdError as error:
        raise _http(error) from error
    return _to_dto(session, current_user, household)


@router.post("/leave", status_code=204)
def leave_household(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Leave the household. The owner must transfer or remove others first."""
    service = HouseholdService(session)
    try:
        service.leave(current_user)
    except HouseholdError as error:
        raise _http(error) from error


@router.delete("/members/{member_user_id}", status_code=204)
def remove_member(
    member_user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a member. Owner only."""
    service = HouseholdService(session)
    try:
        service.remove_member(current_user, member_user_id)
    except HouseholdError as error:
        raise _http(error) from error


@router.post("/transfer", response_model=HouseholdDTO)
def transfer_household(
    body: HouseholdTransferDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HouseholdDTO:
    """Give ownership to a member. The shared plan and shopping list move with it."""
    service = HouseholdService(session)
    try:
        household = service.transfer(current_user, body.user_id)
    except HouseholdError as error:
        raise _http(error) from error
    return _to_dto(session, current_user, household)


@router.post("/recipes/{recipe_id}/share", status_code=204)
def share_recipe(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Share one of the caller's recipes with the household cookbook."""
    service = HouseholdService(session)
    try:
        service.share_recipe(current_user, recipe_id)
    except HouseholdError as error:
        raise _http(error) from error


@router.delete("/recipes/{recipe_id}/share", status_code=204)
def unshare_recipe(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a recipe from the household cookbook. The recipe itself stays."""
    service = HouseholdService(session)
    try:
        service.unshare_recipe(current_user, recipe_id)
    except HouseholdError as error:
        raise _http(error) from error


def _invite_dto(invite: HouseholdInvite) -> HouseholdInviteDTO:
    return HouseholdInviteDTO(
        id=invite.id,
        code=invite.code,
        email=invite.email,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )
