"""Household sharing: membership, invites, recipe visibility, and Pro coverage."""

import math
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.dtos.recipe_dtos import RecipeFilterDTO
from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.user import User
from app.repositories.meal_repo import MealRepo
from app.services.household.scope import effective_access, kitchen_user_id
from app.services.household.service import (
    HouseholdAlreadyMemberError,
    HouseholdForbiddenError,
    HouseholdFullError,
    HouseholdService,
    InviteInvalidError,
    MAX_HOUSEHOLD_MEMBERS,
)
from app.core.usage_limits import get_monthly_limit
from app.core import usage_limits
from app.services.household.usage_meter import (
    bind_household_meter,
    resolve_usage_meter,
    shared_household_limit,
)
from app.services.recipe_service import RecipeInUseError, RecipeService
from app.services.usage_service import UsageService


def _user(session: Session, suffix: str, **overrides) -> User:
    data = dict(
        clerk_id=f"clerk_{suffix}",
        email=f"{suffix}@example.com",
        name=suffix,
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
    )
    data.update(overrides)
    user = User(**data)
    session.add(user)
    session.flush()
    return user


def _recipe(session: Session, owner: User, name: str) -> Recipe:
    recipe = Recipe(
        recipe_name=name,
        recipe_category="Dinner",
        meal_type="Dinner",
        user_id=owner.id,
        directions="Cook it.",
    )
    session.add(recipe)
    session.flush()
    return recipe


class TestHouseholdMembership:
    def test_create_invite_join_and_kitchen_scope(self, db_session: Session):
        owner = _user(db_session, "owner", subscription_tier="pro", subscription_status="active")
        guest = _user(db_session, "guest")
        service = HouseholdService(db_session)

        household = service.create(owner, "Weeknight kitchen")
        assert household.owner_user_id == owner.id
        invite = service.create_invite(owner, email="guest@example.com")

        with pytest.raises(InviteInvalidError, match="different email"):
            service.join(_user(db_session, "stranger"), invite.code)

        joined = service.join(guest, invite.code)
        assert joined.id == household.id
        assert kitchen_user_id(db_session, guest) == owner.id
        assert service.role_for(guest, household) == "member"

        has_pro, reason = effective_access(db_session, guest)
        assert has_pro is True
        assert reason == "household"

        # The guest's own counters stay theirs; coverage does not rewrite the user row.
        assert guest.has_pro_access is False

    def test_free_owner_does_not_cover_a_member(self, db_session: Session):
        owner = _user(db_session, "freeowner")
        guest = _user(db_session, "freeguest")
        service = HouseholdService(db_session)
        service.create(owner, "Free kitchen")
        invite = service.create_invite(owner, email=None)
        service.join(guest, invite.code)

        has_pro, reason = effective_access(db_session, guest)
        assert has_pro is False
        assert reason == "free"

    def test_member_pro_is_kept_when_owner_is_free(self, db_session: Session):
        owner = _user(db_session, "plain")
        guest = _user(db_session, "paid", subscription_tier="pro", subscription_status="active")
        service = HouseholdService(db_session)
        service.create(owner, "Mixed")
        service.join(guest, service.create_invite(owner, None).code)

        has_pro, reason = effective_access(db_session, guest)
        assert has_pro is True
        assert reason == "subscription"

    def test_email_invite_and_expired_code(self, db_session: Session):
        owner = _user(db_session, "host")
        guest = _user(db_session, "pal")
        service = HouseholdService(db_session)
        service.create(owner, "Home")
        invite = service.create_invite(owner, "pal@example.com")
        invite.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.flush()

        with pytest.raises(InviteInvalidError, match="expired"):
            service.join(guest, invite.code)

    def test_cannot_join_a_second_household(self, db_session: Session):
        owner = _user(db_session, "a")
        other = _user(db_session, "b")
        guest = _user(db_session, "c")
        service = HouseholdService(db_session)
        service.create(owner, "First")
        service.join(guest, service.create_invite(owner, None).code)
        service.create(other, "Second")
        with pytest.raises(HouseholdAlreadyMemberError):
            service.join(guest, service.create_invite(other, None).code)

    def test_owner_cannot_leave_while_members_remain(self, db_session: Session):
        owner = _user(db_session, "boss")
        guest = _user(db_session, "cook")
        service = HouseholdService(db_session)
        service.create(owner, "Shared")
        service.join(guest, service.create_invite(owner, None).code)
        with pytest.raises(HouseholdForbiddenError, match="Transfer"):
            service.leave(owner)
        service.remove_member(owner, guest.id)
        service.leave(owner)
        assert service.get_for_user(owner) is None
        assert kitchen_user_id(db_session, guest) == guest.id

    def test_transfer_moves_the_planner(self, db_session: Session):
        owner = _user(db_session, "from")
        guest = _user(db_session, "to")
        service = HouseholdService(db_session)
        household = service.create(owner, "Moving")
        recipe = _recipe(db_session, owner, "Soup")
        meal = Meal(meal_name="Soup night", main_recipe_id=recipe.id, user_id=owner.id, is_saved=True)
        db_session.add(meal)
        db_session.flush()
        entry = PlannerEntry(meal_id=meal.id, user_id=owner.id, position=0)
        db_session.add(entry)
        db_session.flush()

        service.join(guest, service.create_invite(owner, None).code)
        service.transfer(owner, guest.id)

        db_session.refresh(entry)
        db_session.refresh(meal)
        db_session.refresh(household)
        assert household.owner_user_id == guest.id
        assert entry.user_id == guest.id
        assert meal.user_id == guest.id
        assert kitchen_user_id(db_session, owner) == guest.id
        assert service.role_for(owner, household) == "member"

    def test_member_cap(self, db_session: Session):
        owner = _user(db_session, "cap")
        service = HouseholdService(db_session)
        service.create(owner, "Full")
        for index in range(MAX_HOUSEHOLD_MEMBERS - 1):
            person = _user(db_session, f"m{index}")
            service.join(person, service.create_invite(owner, None).code)
        extra = _user(db_session, "overflow")
        with pytest.raises(HouseholdFullError, match="up to"):
            service.join(extra, service.create_invite(owner, None).code)


class TestSharedRecipes:
    def test_shared_recipe_is_visible_but_not_editable_by_members(self, db_session: Session):
        owner = _user(db_session, "chef")
        guest = _user(db_session, "diner")
        service = HouseholdService(db_session)
        service.create(owner, "Cookbook")
        service.join(guest, service.create_invite(owner, None).code)
        recipe = _recipe(db_session, owner, "Shared chili")
        private = _recipe(db_session, owner, "Private chili")
        service.share_recipe(owner, recipe.id)

        guest_recipes = RecipeService(db_session, guest.id)
        visible = guest_recipes.list_filtered(RecipeFilterDTO(), include_shared=True)
        names = {item.recipe_name for item in visible}
        assert "Shared chili" in names
        assert "Private chili" not in names
        assert guest_recipes.get_recipe(recipe.id, include_shared=True) is not None
        assert guest_recipes.get_recipe(private.id, include_shared=True) is None
        assert guest_recipes.get_recipe(recipe.id) is None

    def test_shared_recipe_can_anchor_the_owners_meal(self, db_session: Session):
        owner = _user(db_session, "planowner")
        guest = _user(db_session, "planguest")
        service = HouseholdService(db_session)
        service.create(owner, "Plan")
        service.join(guest, service.create_invite(owner, None).code)
        recipe = _recipe(db_session, guest, "Guest tacos")
        service.share_recipe(guest, recipe.id)

        valid = MealRepo(db_session).validate_recipe_ids([recipe.id], owner.id)
        assert recipe.id in valid
        assert MealRepo(db_session).validate_recipe_ids([recipe.id], _user(db_session, "outsider").id) == []

    def test_delete_is_blocked_when_a_household_meal_uses_the_recipe(self, db_session: Session):
        owner = _user(db_session, "mealowner")
        guest = _user(db_session, "mealguest")
        service = HouseholdService(db_session)
        service.create(owner, "Meals")
        service.join(guest, service.create_invite(owner, None).code)
        recipe = _recipe(db_session, guest, "Guest stew")
        service.share_recipe(guest, recipe.id)
        db_session.add(
            Meal(meal_name="Stew", main_recipe_id=recipe.id, user_id=owner.id, is_saved=True)
        )
        db_session.flush()

        with pytest.raises(RecipeInUseError):
            RecipeService(db_session, guest.id).delete_recipe(recipe.id)
        assert RecipeService(db_session, guest.id).get_recipe(recipe.id) is not None

    def test_account_deletion_blocked_for_owner_with_members(self, db_session: Session):
        from app.services.account_service import AccountDeletionBlockedError, AccountService

        owner = _user(db_session, "stuck")
        guest = _user(db_session, "stays")
        service = HouseholdService(db_session)
        service.create(owner, "Cannot delete")
        service.join(guest, service.create_invite(owner, None).code)

        with pytest.raises(AccountDeletionBlockedError, match="Transfer the household"):
            AccountService(db_session).delete_account(owner)


class TestSharedUsageMeter:
    def test_two_members_share_the_owners_pro_pool(self, file_db):
        with file_db() as session:
            owner = session.get(User, 1)
            assert owner is not None
            owner.is_admin = False
            owner.subscription_tier = "free"
            owner.subscription_status = "active"
            guest = User(
                clerk_id="guest_meter",
                email="guest-meter@example.com",
                name="Guest",
                is_admin=False,
                subscription_tier="free",
                subscription_status="active",
            )
            session.add(guest)
            session.commit()

            alone = resolve_usage_meter(session, owner)
            assert alone.shared is False
            assert alone.user_id == owner.id
            assert alone.limit_for("recipes_imported") == get_monthly_limit(
                "free", "recipes_imported"
            )

            service = HouseholdService(session)
            service.create(owner, "Metered kitchen")
            service.join(guest, service.create_invite(owner, None).code)

            owner.subscription_tier = "pro"
            owner.subscription_status = "active"
            session.commit()

            meter = resolve_usage_meter(session, guest)
            assert meter.shared is True
            assert meter.user_id == owner.id
            assert shared_household_limit("recipes_imported") == math.ceil(
                get_monthly_limit("pro", "recipes_imported") * 1.5
            )
            with bind_household_meter(session):
                subject, limit = usage_limits.usage_meter(guest, "recipes_imported")
            assert subject.id == owner.id
            assert limit == shared_household_limit("recipes_imported")

            UsageService(session, subject.id).reserve(
                "recipes_imported", limit
            )
            assert UsageService(session, owner.id).get_usage().recipes_imported == 1
            assert UsageService(session, guest.id).get_usage().recipes_imported == 0

            owner.is_admin = True
            session.commit()
            admin_meter = resolve_usage_meter(session, guest)
            assert admin_meter.shared is True
            with bind_household_meter(session):
                admin_subject, admin_limit = usage_limits.usage_meter(
                    guest, "ai_images_generated"
                )
            assert admin_subject.id == owner.id
            assert admin_limit is None
