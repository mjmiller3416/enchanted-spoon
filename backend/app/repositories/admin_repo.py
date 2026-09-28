"""app/repositories/admin_repo.py

Repository layer for admin operations. Handles direct database interactions
for user management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from ..models.meal import Meal
from ..models.planner_entry import PlannerEntry
from ..models.recipe import Recipe
from ..models.recipe_group import RecipeGroup
from ..models.shopping_item import ShoppingItem
from ..models.user import User
from ..models.user_usage import UserUsage


def _count_if(condition) -> Any:
    """SUM(CASE WHEN condition THEN 1 ELSE 0 END), portable across SQLite/Postgres."""
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


class AdminRepo:
    """Handles direct DB queries for admin operations."""

    def __init__(self, session: Session):
        self.session = session

    # ── User Queries ─────────────────────────────────────────────────────────

    def list_users(
        self, skip: int = 0, limit: int = 50, search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """List users with pagination, optionally filtered.

        ``search`` matches a user id exactly ("12" or "#12", as feedback
        issues cite them) or a case-insensitive substring of email or name.
        """
        filters = []
        term = (search or "").strip()
        if term:
            id_term = term.lstrip("#")
            if id_term.isdigit():
                filters.append(User.id == int(id_term))
            else:
                pattern = f"%{term.lower()}%"
                filters.append(
                    func.lower(User.email).like(pattern)
                    | func.lower(func.coalesce(User.name, "")).like(pattern)
                )

        total = self.session.scalar(select(func.count(User.id)).where(*filters))

        stmt = (
            select(User)
            .where(*filters)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        users = list(self.session.scalars(stmt).all())
        return users, total or 0

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by internal ID."""
        stmt = select(User).where(User.id == user_id)
        return self.session.scalars(stmt).first()

    def list_usage_for_month(
        self, month: str
    ) -> List[Tuple[User, Optional[UserUsage]]]:
        """List every user with their usage row for ``month`` (if any).

        LEFT JOIN users -> user_usage on (user_id, month) so that users with
        no usage row for the requested month still appear (paired with None).
        Ordered by user id.
        """
        stmt = (
            select(User, UserUsage)
            .outerjoin(
                UserUsage,
                and_(
                    UserUsage.user_id == User.id,
                    UserUsage.month == month,
                ),
            )
            .order_by(User.id)
        )
        return [(row[0], row[1]) for row in self.session.execute(stmt).all()]

    def list_activity(
        self, since: datetime
    ) -> List[Tuple[User, Dict[str, Any]]]:
        """List every user with their engagement counts, ordered by user id.

        One grouped subquery per table, LEFT JOINed onto users, so users with
        no rows in a table still appear with zeros. ``since`` bounds the
        ``*_recent`` counts. Starter-pack recipes and meals are excluded.
        """
        recipes = (
            select(
                Recipe.user_id.label("user_id"),
                func.count(Recipe.id).label("recipes"),
                _count_if(Recipe.is_ai_generated.is_(True)).label("recipes_ai_generated"),
                _count_if(Recipe.source_url.is_not(None)).label("recipes_imported"),
                _count_if(Recipe.created_at >= since).label("recipes_recent"),
            )
            .where(Recipe.is_sample.is_(False))
            .group_by(Recipe.user_id)
            .subquery()
        )
        # Favoriting a starter recipe is still the user doing something
        favorites = (
            select(Recipe.user_id.label("user_id"), func.count(Recipe.id).label("favorites"))
            .where(Recipe.is_favorite.is_(True))
            .group_by(Recipe.user_id)
            .subquery()
        )
        collections = (
            select(RecipeGroup.user_id.label("user_id"), func.count(RecipeGroup.id).label("collections"))
            .group_by(RecipeGroup.user_id)
            .subquery()
        )
        meals = (
            select(Meal.user_id.label("user_id"), func.count(Meal.id).label("saved_meals"))
            .where(Meal.is_saved.is_(True), Meal.is_sample.is_(False))
            .group_by(Meal.user_id)
            .subquery()
        )
        # Cleared entries are soft-deleted precisely so cooking history survives
        planner = (
            select(
                PlannerEntry.user_id.label("user_id"),
                _count_if(
                    and_(PlannerEntry.is_completed.is_(False), PlannerEntry.is_cleared.is_(False))
                ).label("planned_meals"),
                _count_if(PlannerEntry.is_completed.is_(True)).label("meals_cooked"),
                _count_if(
                    and_(PlannerEntry.is_completed.is_(True), PlannerEntry.completed_at >= since)
                ).label("meals_cooked_recent"),
                func.max(PlannerEntry.completed_at).label("last_cooked_at"),
            )
            .group_by(PlannerEntry.user_id)
            .subquery()
        )
        shopping = (
            select(ShoppingItem.user_id.label("user_id"), func.count(ShoppingItem.id).label("shopping_items"))
            .group_by(ShoppingItem.user_id)
            .subquery()
        )

        columns = [
            recipes.c.recipes,
            recipes.c.recipes_ai_generated,
            recipes.c.recipes_imported,
            recipes.c.recipes_recent,
            favorites.c.favorites,
            collections.c.collections,
            meals.c.saved_meals,
            planner.c.planned_meals,
            planner.c.meals_cooked,
            planner.c.meals_cooked_recent,
            planner.c.last_cooked_at,
            shopping.c.shopping_items,
        ]
        stmt = select(User, *columns)
        for sub in (recipes, favorites, collections, meals, planner, shopping):
            stmt = stmt.outerjoin(sub, sub.c.user_id == User.id)
        stmt = stmt.order_by(User.id)

        names = [c.name for c in columns]
        return [
            (row[0], dict(zip(names, row[1:])))
            for row in self.session.execute(stmt).all()
        ]

    def update_user_pro_grant(
        self,
        user: User,
        granted_pro_until: datetime,
        granted_by: str,
    ) -> User:
        """Grant pro access to a user. Flushes only."""
        user.granted_pro_until = granted_pro_until
        user.granted_by = granted_by
        self.session.flush()
        return user

    def revoke_user_pro_grant(self, user: User) -> User:
        """Revoke granted pro access from a user. Flushes only."""
        user.granted_pro_until = None
        user.granted_by = None
        self.session.flush()
        return user

    def update_user_admin_flag(self, user: User, is_admin: bool) -> User:
        """Update admin flag on a user. Flushes only."""
        user.is_admin = is_admin
        self.session.flush()
        return user

    def delete_user(self, user: User) -> None:
        """Delete a user (cascade handles related data). Flushes only."""
        self.session.delete(user)
        self.session.flush()

