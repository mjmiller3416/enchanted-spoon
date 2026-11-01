"""Create households, invite members, and share recipes.

Services commit. Repositories are not used here because the operations are
small and always include the membership rules.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...models.household import (
    Household,
    HouseholdInvite,
    HouseholdMember,
    HouseholdRecipeShare,
)
from ...models.meal import Meal
from ...models.planner_entry import PlannerEntry
from ...models.recipe import Recipe
from ...models.shopping_item import ShoppingItem
from ...models.shopping_note import ShoppingNote
from ...models.user import User
from .scope import membership_for

ROLE_OWNER = "owner"
ROLE_MEMBER = "member"
MAX_HOUSEHOLD_MEMBERS = 8
MAX_OPEN_INVITES = 10
INVITE_DAYS = 14


class HouseholdError(Exception):
    """Base error for household operations."""


class HouseholdAlreadyMemberError(HouseholdError):
    """The user is already in a household."""


class HouseholdNotFoundError(HouseholdError):
    """No household matches the request."""


class HouseholdForbiddenError(HouseholdError):
    """The user cannot perform this action."""


class HouseholdFullError(HouseholdError):
    """The household is at its member cap."""


class InviteInvalidError(HouseholdError):
    """The invite code cannot be redeemed."""


class RecipeShareError(HouseholdError):
    """A recipe cannot be shared or unshared."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class HouseholdService:
    """Household membership, invites, and recipe shares."""

    def __init__(self, session: Session):
        self.session = session

    def get_for_user(self, user: User) -> Optional[Household]:
        """Household the user belongs to, if any."""
        member = membership_for(self.session, user.id)
        if member is None:
            return None
        return self.session.get(Household, member.household_id)

    def role_for(self, user: User, household: Household) -> Optional[str]:
        member = membership_for(self.session, user.id)
        if member is None or member.household_id != household.id:
            return None
        return member.role

    def create(self, user: User, name: str) -> Household:
        """Create a household and make ``user`` the owner."""
        if membership_for(self.session, user.id) is not None:
            raise HouseholdAlreadyMemberError(
                "Leave your current household before creating a new one."
            )
        cleaned = name.strip()
        if not cleaned:
            raise HouseholdError("Give the household a name.")
        household = Household(name=cleaned[:80], owner_user_id=user.id)
        self.session.add(household)
        self.session.flush()
        self.session.add(
            HouseholdMember(
                household_id=household.id,
                user_id=user.id,
                role=ROLE_OWNER,
            )
        )
        self._commit()
        return household

    def rename(self, user: User, name: str) -> Household:
        household = self._require_owner(user)
        cleaned = name.strip()
        if not cleaned:
            raise HouseholdError("Give the household a name.")
        household.name = cleaned[:80]
        self._commit()
        return household

    def dissolve(self, user: User) -> None:
        """Delete the household. Shared recipes stay with their owners.

        The meal plan and shopping list already live on the owner, so they
        remain that person's personal plan.
        """
        household = self._require_owner(user)
        self.session.delete(household)
        self._commit()

    def create_invite(self, user: User, email: Optional[str]) -> HouseholdInvite:
        household = self._require_owner(user)
        self._require_room(household)
        open_invites = self.session.scalars(
            select(HouseholdInvite).where(
                HouseholdInvite.household_id == household.id,
                HouseholdInvite.accepted_at.is_(None),
                HouseholdInvite.revoked_at.is_(None),
            )
        ).all()
        active = [invite for invite in open_invites if _as_utc(invite.expires_at) > _utcnow()]
        if len(active) >= MAX_OPEN_INVITES:
            raise HouseholdError("Revoke an unused invite before creating another.")

        invite = HouseholdInvite(
            household_id=household.id,
            code=self._new_code(),
            email=email,
            created_by_user_id=user.id,
            expires_at=_utcnow() + timedelta(days=INVITE_DAYS),
        )
        self.session.add(invite)
        self._commit()
        return invite

    def revoke_invite(self, user: User, invite_id: int) -> None:
        household = self._require_owner(user)
        invite = self.session.get(HouseholdInvite, invite_id)
        if invite is None or invite.household_id != household.id:
            raise InviteInvalidError("That invite was not found.")
        if invite.accepted_at is None and invite.revoked_at is None:
            invite.revoked_at = _utcnow()
            self._commit()

    def join(self, user: User, code: str) -> Household:
        """Redeem an invite code."""
        if membership_for(self.session, user.id) is not None:
            raise HouseholdAlreadyMemberError(
                "Leave your current household before joining another."
            )
        cleaned = code.strip()
        invite = self.session.scalars(
            select(HouseholdInvite).where(HouseholdInvite.code == cleaned)
        ).first()
        if invite is None:
            raise InviteInvalidError("That invite code is not valid.")
        if invite.revoked_at is not None or invite.accepted_at is not None:
            raise InviteInvalidError("That invite is no longer valid.")
        if _as_utc(invite.expires_at) <= _utcnow():
            raise InviteInvalidError("That invite has expired.")
        if invite.email and invite.email.lower() != (user.email or "").lower():
            raise InviteInvalidError(
                "That invite was created for a different email address."
            )

        household = self.session.get(Household, invite.household_id)
        if household is None:
            raise InviteInvalidError("That invite is no longer valid.")
        self._require_room(household)

        self.session.add(
            HouseholdMember(
                household_id=household.id,
                user_id=user.id,
                role=ROLE_MEMBER,
            )
        )
        invite.accepted_at = _utcnow()
        invite.accepted_by_user_id = user.id
        self._commit()
        return household

    def leave(self, user: User) -> None:
        """Leave the household. The owner must transfer or remove everyone first."""
        member = membership_for(self.session, user.id)
        if member is None:
            raise HouseholdNotFoundError("You are not in a household.")
        household = self.session.get(Household, member.household_id)
        if household is None:
            raise HouseholdNotFoundError("You are not in a household.")
        if member.role == ROLE_OWNER:
            others = [
                m for m in self._members(household.id) if m.user_id != user.id
            ]
            if others:
                raise HouseholdForbiddenError(
                    "Transfer ownership or remove the other members before leaving."
                )
            self.session.delete(household)
            self._commit()
            return
        self.session.delete(member)
        self._commit()

    def remove_member(self, user: User, member_user_id: int) -> None:
        household = self._require_owner(user)
        if member_user_id == user.id:
            raise HouseholdForbiddenError("Use leave to remove yourself.")
        member = self.session.scalars(
            select(HouseholdMember).where(
                HouseholdMember.household_id == household.id,
                HouseholdMember.user_id == member_user_id,
            )
        ).first()
        if member is None:
            raise HouseholdNotFoundError("That person is not in your household.")
        self.session.delete(member)
        self._commit()

    def transfer(self, user: User, new_owner_user_id: int) -> Household:
        """Make another member the owner and move the shared kitchen onto them.

        Planner entries, meals, shopping items, and shopping notes that lived
        on the previous owner move with the household. Rows that would collide
        with the new owner's existing shopping items stay on the previous owner.
        """
        household = self._require_owner(user)
        if new_owner_user_id == user.id:
            return household
        member = self.session.scalars(
            select(HouseholdMember).where(
                HouseholdMember.household_id == household.id,
                HouseholdMember.user_id == new_owner_user_id,
            )
        ).first()
        if member is None or member.role == ROLE_OWNER:
            raise HouseholdNotFoundError("Choose a member of this household.")

        current = membership_for(self.session, user.id)
        if current is None:
            raise HouseholdForbiddenError("Only the owner can transfer the household.")
        old_owner_id = household.owner_user_id
        current.role = ROLE_MEMBER
        member.role = ROLE_OWNER
        household.owner_user_id = new_owner_user_id
        self._move_kitchen(old_owner_id, new_owner_user_id)
        self._commit()
        return household

    def share_recipe(self, user: User, recipe_id: int) -> HouseholdRecipeShare:
        household = self._require_member(user)
        recipe = self.session.get(Recipe, recipe_id)
        if recipe is None or recipe.user_id != user.id:
            raise RecipeShareError("You can only share recipes you created.")
        existing = self.session.scalars(
            select(HouseholdRecipeShare).where(
                HouseholdRecipeShare.household_id == household.id,
                HouseholdRecipeShare.recipe_id == recipe_id,
            )
        ).first()
        if existing is not None:
            return existing
        share = HouseholdRecipeShare(
            household_id=household.id,
            recipe_id=recipe_id,
            shared_by_user_id=user.id,
        )
        self.session.add(share)
        self._commit()
        return share

    def unshare_recipe(self, user: User, recipe_id: int) -> None:
        household = self._require_member(user)
        share = self.session.scalars(
            select(HouseholdRecipeShare).where(
                HouseholdRecipeShare.household_id == household.id,
                HouseholdRecipeShare.recipe_id == recipe_id,
            )
        ).first()
        if share is None:
            return
        if share.shared_by_user_id != user.id and self.role_for(user, household) != ROLE_OWNER:
            raise RecipeShareError("Only the person who shared this recipe can unshare it.")
        self.session.delete(share)
        self._commit()

    def prepare_account_deletion(self, user: User) -> None:
        """Block deletion of an owner who still has members; drop a solo household.

        Membership rows of a non-owner cascade when the user row is deleted.
        """
        member = membership_for(self.session, user.id)
        if member is None or member.role != ROLE_OWNER:
            return
        household = self.session.get(Household, member.household_id)
        if household is None:
            return
        others = [m for m in self._members(household.id) if m.user_id != user.id]
        if others:
            raise HouseholdForbiddenError(
                "Transfer the household or remove the other members before deleting your account."
            )
        self.session.delete(household)
        self.session.flush()

    def members(self, household_id: int) -> list[HouseholdMember]:
        return self._members(household_id)

    def open_invites(self, household_id: int) -> list[HouseholdInvite]:
        invites = self.session.scalars(
            select(HouseholdInvite)
            .where(
                HouseholdInvite.household_id == household_id,
                HouseholdInvite.accepted_at.is_(None),
                HouseholdInvite.revoked_at.is_(None),
            )
            .order_by(HouseholdInvite.created_at.desc())
        ).all()
        return [invite for invite in invites if _as_utc(invite.expires_at) > _utcnow()]

    def _members(self, household_id: int) -> list[HouseholdMember]:
        return list(
            self.session.scalars(
                select(HouseholdMember)
                .where(HouseholdMember.household_id == household_id)
                .order_by(HouseholdMember.joined_at.asc())
            ).all()
        )

    def _require_member(self, user: User) -> Household:
        household = self.get_for_user(user)
        if household is None:
            raise HouseholdNotFoundError("Create or join a household first.")
        return household

    def _require_owner(self, user: User) -> Household:
        household = self._require_member(user)
        if self.role_for(user, household) != ROLE_OWNER:
            raise HouseholdForbiddenError("Only the household owner can do that.")
        return household

    def _require_room(self, household: Household) -> None:
        if len(self._members(household.id)) >= MAX_HOUSEHOLD_MEMBERS:
            raise HouseholdFullError(
                f"A household can have up to {MAX_HOUSEHOLD_MEMBERS} people."
            )

    def _new_code(self) -> str:
        for _ in range(5):
            code = secrets.token_urlsafe(9)
            taken = self.session.scalars(
                select(HouseholdInvite.id).where(HouseholdInvite.code == code)
            ).first()
            if taken is None:
                return code
        raise HouseholdError("Could not create an invite. Please try again.")

    def _move_kitchen(self, old_owner_id: int, new_owner_id: int) -> None:
        self.session.execute(
            update(PlannerEntry)
            .where(PlannerEntry.user_id == old_owner_id)
            .values(user_id=new_owner_id)
        )
        self.session.execute(
            update(Meal).where(Meal.user_id == old_owner_id).values(user_id=new_owner_id)
        )
        existing_keys = select(ShoppingItem.aggregation_key).where(
            ShoppingItem.user_id == new_owner_id,
            ShoppingItem.aggregation_key.is_not(None),
        )
        self.session.execute(
            update(ShoppingItem)
            .where(ShoppingItem.user_id == old_owner_id)
            .where(
                or_(
                    ShoppingItem.aggregation_key.is_(None),
                    ShoppingItem.aggregation_key.not_in(existing_keys),
                )
            )
            .values(user_id=new_owner_id)
        )
        old_note = self.session.get(ShoppingNote, old_owner_id)
        if old_note is None:
            return
        new_note = self.session.get(ShoppingNote, new_owner_id)
        content = old_note.content or ""
        self.session.delete(old_note)
        self.session.flush()
        if new_note is None:
            self.session.add(ShoppingNote(user_id=new_owner_id, content=content))
        elif content and content not in (new_note.content or ""):
            combined = f"{new_note.content.rstrip()}\n{content}".strip()
            new_note.content = combined

    def _commit(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
