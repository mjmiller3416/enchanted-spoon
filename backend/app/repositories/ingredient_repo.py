"""app/core/repositories/ingredient_repo.py

Provides database operations for Ingredient entities.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.ingredient import Ingredient


# ── Ingredient Repository ───────────────────────────────────────────────────────────────────────────────────
class IngredientRepo:
    """Handles ingredient-specific database operations.

    All operations are scoped to a specific user for multi-tenant isolation.
    """

    def __init__(self, session: Session, user_id: int):
        """Initialize the Ingredient Repository with a database session and user ID.

        Args:
            session: SQLAlchemy database session
            user_id: The ID of the current user for data isolation
        """
        self.session = session
        self.user_id = user_id

    # ── CRUD Operations ─────────────────────────────────────────────────────────────────────────────────────
    def get_all(self) -> list[Ingredient]:
        """
        Return all ingredients for the current user.

        Returns:
            list[Ingredient]: A list of all ingredients owned by the current user.
        """
        stmt = select(Ingredient).where(Ingredient.user_id == self.user_id)
        return self.session.execute(stmt).scalars().unique().all()

    def get_by_id(self, ingredient_id: int) -> Ingredient | None:
        """
        Fetch a single ingredient by ID, scoped to current user.

        Args:
            ingredient_id (int): The ID of the ingredient to retrieve.

        Returns:
            Ingredient | None: The ingredient if owned by current user, or None.
        """
        stmt = select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.user_id == self.user_id
        )
        return self.session.execute(stmt).scalars().first()

    def delete(self, ingredient: Ingredient) -> None:
        """Delete the provided ingredient."""
        self.session.delete(ingredient)

    def add(self, ingredient: Ingredient) -> None:
        """Add a new ingredient to the session."""
        self.session.add(ingredient)

    # ── Search and Retrieval ────────────────────────────────────────────────────────────────────────────────
    def find_by_name_category(self, name: str, category: str) -> Ingredient | None:
        """
        Return a single matching ingredient by name+category (case-insensitive).

        Args:
            name (str): The name of the ingredient to search for.
            category (str): The category of the ingredient to search for.

        Returns:
            Ingredient | None: The matching ingredient, or None if not found.
        """
        stmt = (
            select(Ingredient)
            .where(Ingredient.user_id == self.user_id)
            # Exact case-insensitive match: ilike() would treat % and _ in a
            # name as wildcards and link the wrong ingredient
            .where(func.lower(Ingredient.ingredient_name) == name.strip().lower())
            .where(func.lower(Ingredient.ingredient_category) == category.strip().lower())
        )
        return self.session.execute(stmt).scalars().unique().first()

    def search_by_name(self, term: str, category: str | None = None) -> list[Ingredient]:
        """
        Search for ingredients with name containing a term (optionally filtered by category).

        Args:
            term (str): The search term to look for in ingredient names.
            category (str | None): The category to filter by, if provided.

        Returns:
            list[Ingredient]: A list of ingredients matching the search criteria.
        """
        stmt = select(Ingredient).where(
            Ingredient.user_id == self.user_id,
            Ingredient.ingredient_name.ilike(f"%{term.strip()}%")
        )
        if category:
            stmt = stmt.where(
                func.lower(Ingredient.ingredient_category) == category.strip().lower()
            )
        return self.session.execute(stmt).scalars().unique().all()

    def find_category_by_names(self, names: list[str]) -> str | None:
        """
        Return the category the user files an ingredient under, by exact name.

        Matches case-insensitively against any of ``names`` (callers pass a few
        spellings, e.g. "eggs" and "egg"). When the ingredient exists under more
        than one category, a specific one wins over "other"; ties go to the
        oldest row so the answer is stable.

        Args:
            names (list[str]): Candidate ingredient names to look up.

        Returns:
            str | None: The ingredient's category, or None if no name matches.
        """
        candidates = {n.strip().lower() for n in names if n and n.strip()}
        if not candidates:
            return None

        stmt = (
            select(Ingredient.ingredient_category)
            .where(Ingredient.user_id == self.user_id)
            # Exact match, not ilike(): % and _ in a name must not act as wildcards
            .where(func.lower(Ingredient.ingredient_name).in_(candidates))
            .order_by(Ingredient.id)
        )
        categories = [c for c in self.session.execute(stmt).scalars().all() if c]
        if not categories:
            return None
        specific = [c for c in categories if c.strip().lower() != "other"]
        return (specific or categories)[0]

    def get_distinct_names(self) -> list[str]:
        """
        Return a list of all unique ingredient names for the current user.

        Returns:
            list[str]: A list of distinct ingredient names.
        """
        stmt = (
            select(Ingredient.ingredient_name)
            .where(Ingredient.user_id == self.user_id)
            .distinct()
        )
        results = self.session.execute(stmt).scalars().all()
        return results

    def get_or_create(self, dto) -> Ingredient:
        """
        Get existing ingredient or create new one based on name and category.

        Args:
            dto: Data Transfer Object containing ingredient_name and ingredient_category.

        Returns:
            Ingredient: The existing ingredient if found, or a new Ingredient instance.
        """
        existing = self.find_by_name_category(dto.ingredient_name, dto.ingredient_category)
        if existing:
            return existing

        new_ingredient = Ingredient(
            ingredient_name=dto.ingredient_name,
            ingredient_category=dto.ingredient_category,
            user_id=self.user_id
        )
        self.add(new_ingredient)
        # flush so SQLAlchemy assigns an ID and the new ingredient is queryable immediately
        self.session.flush()
        return new_ingredient
