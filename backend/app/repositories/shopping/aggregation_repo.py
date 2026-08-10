"""app/repositories/shopping/aggregation_repo.py

Repository for shopping list aggregation operations.
Handles recipe ingredient aggregation, queries, and summary statistics.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload

from ...models.ingredient import Ingredient
from ...models.recipe import Recipe
from ...models.recipe_ingredient import RecipeIngredient
from ...models.shopping_item import ShoppingItem
from ...models.shopping_item_contribution import ShoppingItemContribution
from ...utils.unit_conversion import get_dimension, to_base_unit, to_display_unit

# Safety backstop for list queries that omit an explicit limit.
MAX_LIST_ROWS = 1000


# ── Data Classes for Aggregation ────────────────────────────────────────────────────────────────────────────
@dataclass
class AggregatedIngredient:
    """Data class for aggregated ingredient data."""
    name: str
    category: Optional[str]
    dimension: str
    base_quantity: float
    original_unit: Optional[str]
    recipe_ids: set  # Set of recipe IDs that contribute


@dataclass
class ContributionData:
    """Data class for a single contribution to a shopping item."""
    recipe_id: int
    planner_entry_id: int
    base_quantity: float
    dimension: str
    original_unit: str | None = None
    category: str | None = None


# ── Shopping Aggregation Repository ─────────────────────────────────────────────────────────────────────────
class ShoppingAggregationRepo:
    """Repository for shopping list aggregation and query operations."""

    def __init__(self, session: Session, user_id: int):
        """Initialize the Shopping Aggregation Repository.

        Args:
            session: SQLAlchemy database session
            user_id: The ID of the current user for multi-tenant isolation
        """
        self.session = session
        self.user_id = user_id

    # ── Recipe Ingredient Aggregation ───────────────────────────────────────────────────────────────────────
    def get_recipe_ingredients(self, recipe_ids: List[int]) -> List[RecipeIngredient]:
        """
        Fetch all recipe ingredients for given recipe IDs.
        Handles duplicate recipe IDs by counting occurrences and scaling quantities.

        Args:
            recipe_ids (List[int]): List of recipe IDs to fetch ingredients for.

        Returns:
            List[RecipeIngredient]: List of RecipeIngredient objects with loaded relationships.
        """
        if not recipe_ids:
            return []

        # Count occurrences of each recipe ID
        from collections import Counter
        recipe_counts = Counter(recipe_ids)
        unique_recipe_ids = list(recipe_counts.keys())

        stmt = select(RecipeIngredient).where(
            RecipeIngredient.recipe_id.in_(unique_recipe_ids)
        ).options(
            joinedload(RecipeIngredient.ingredient),
            joinedload(RecipeIngredient.recipe)
        )
        recipe_ingredients = self.session.scalars(stmt).unique().all()

        # Duplicate recipe ingredients based on count
        result = []
        for ri in recipe_ingredients:
            count = recipe_counts[ri.recipe_id]
            for _ in range(count):
                result.append(ri)

        return result

    def aggregate_ingredients_for_entry(
        self,
        recipe_ids: List[int],
        planner_entry_id: int,
        category_filter: Optional[str] = None
    ) -> Dict[str, List[ContributionData]]:
        """
        Aggregate ingredients from recipes for a single planner entry.
        Returns contribution data grouped by aggregation_key.

        Args:
            recipe_ids: List of recipe IDs in this entry
            planner_entry_id: The planner entry ID
            category_filter: If provided, only include ingredients matching this category

        Returns:
            Dict mapping aggregation_key to list of ContributionData
        """
        recipe_ingredients = self.get_recipe_ingredients(recipe_ids)
        contributions: Dict[str, List[ContributionData]] = defaultdict(list)

        for ri in recipe_ingredients:
            ingredient: Ingredient = ri.ingredient

            # Skip if category filter doesn't match
            if category_filter and ingredient.ingredient_category != category_filter:
                continue

            dimension = get_dimension(ri.unit)
            agg_key = ShoppingItem.make_aggregation_key(ingredient.ingredient_name, dimension)

            # Convert to base unit for aggregation
            base_qty, _ = to_base_unit(ri.quantity or 0.0, ri.unit)

            contributions[agg_key].append(ContributionData(
                recipe_id=ri.recipe_id,
                planner_entry_id=planner_entry_id,
                base_quantity=base_qty,
                dimension=dimension,
                original_unit=ri.unit,
                category=ingredient.ingredient_category,
            ))

        return contributions

    def aggregate_ingredients(
        self,
        recipe_ids: List[int],
        category_filter: Optional[str] = None
    ) -> List[AggregatedIngredient]:
        """
        Aggregate ingredients from recipes into AggregatedIngredient objects.
        Groups by (ingredient_name, dimension) to properly handle different unit types.

        Args:
            recipe_ids: List of recipe IDs to aggregate ingredients from.
            category_filter: If provided, only include ingredients matching this category.

        Returns:
            List of AggregatedIngredient objects.
        """
        recipe_ingredients = self.get_recipe_ingredients(recipe_ids)

        # Aggregate by (ingredient_name, dimension)
        aggregation: Dict[str, AggregatedIngredient] = {}

        for ri in recipe_ingredients:
            ingredient: Ingredient = ri.ingredient

            # Skip if category filter doesn't match
            if category_filter and ingredient.ingredient_category != category_filter:
                continue

            dimension = get_dimension(ri.unit)
            agg_key = ShoppingItem.make_aggregation_key(ingredient.ingredient_name, dimension)

            # Convert to base unit for aggregation
            base_qty, _ = to_base_unit(ri.quantity or 0.0, ri.unit)

            if agg_key not in aggregation:
                aggregation[agg_key] = AggregatedIngredient(
                    name=ingredient.ingredient_name,
                    category=ingredient.ingredient_category,
                    dimension=dimension,
                    base_quantity=0.0,
                    original_unit=ri.unit,
                    recipe_ids=set()
                )

            data = aggregation[agg_key]
            data.base_quantity += base_qty
            data.original_unit = ri.unit or data.original_unit
            data.recipe_ids.add(ri.recipe_id)

        return list(aggregation.values())

    def get_ingredient_breakdown(
            self,
            recipe_ids: List[int]
        ) -> Dict[str, List[Tuple[str, float, str, int]]]:
        """
        Get detailed breakdown of ingredients used in recipes.
        Groups by (ingredient, dimension) to properly handle different unit types.

        Args:
            recipe_ids (List[int]): List of recipe IDs to get breakdown for.

        Returns:
            Dict[str, List[Tuple[str, float, str, int]]]: Breakdown by ingredient key.
                Each tuple is (recipe_name, quantity, unit, usage_count).
        """
        recipe_ingredients = self.get_recipe_ingredients(recipe_ids)
        breakdown: Dict[str, List[Tuple[str, float, str, int]]] = defaultdict(list)

        # Aggregate by (ingredient, dimension, recipe) to combine duplicate recipes
        # Key: (ingredient_name, dimension, recipe_name)
        recipe_aggregation: Dict[Tuple[str, str, str], Dict[str, Any]] = defaultdict(lambda: {
            "base_quantity": 0.0,
            "dimension": None,
            "original_unit": None,
            "usage_count": 0,
        })

        for ri in recipe_ingredients:
            ingredient = ri.ingredient
            recipe = ri.recipe
            dimension = get_dimension(ri.unit)

            # convert to base unit for aggregation
            base_qty, _ = to_base_unit(ri.quantity or 0.0, ri.unit)

            agg_key = (ingredient.ingredient_name, dimension, recipe.recipe_name)
            data = recipe_aggregation[agg_key]
            data["base_quantity"] += base_qty
            data["dimension"] = dimension
            data["original_unit"] = ri.unit or data["original_unit"]
            data["usage_count"] += 1

        # Convert aggregated data to the expected format
        for (ingredient_name, dimension, recipe_name), data in recipe_aggregation.items():
            # convert from base unit to display unit
            display_qty, display_unit = to_display_unit(
                data["base_quantity"], data["dimension"], data["original_unit"]
            )

            # create breakdown key using dimension
            ingredient_key = ShoppingItem.make_aggregation_key(ingredient_name, dimension)
            breakdown[ingredient_key].append((recipe_name, display_qty, display_unit, data["usage_count"]))

        return breakdown

    # ── Shopping Item Search and Filter ─────────────────────────────────────────────────────────────────────
    def search_shopping_items(
        self,
        user_id: Optional[int] = None,
        search_term: Optional[str] = None,
        source: Optional[str] = None,
        category: Optional[str] = None,
        have: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
        ) -> List[ShoppingItem]:
        """
        Search shopping items with filters for a specific user.

        Args:
            user_id (Optional[int]): ID of the user whose items to search. Defaults to self.user_id.
            search_term (Optional[str]): Search in ingredient names.
            source (Optional[str]): Filter by source.
            category (Optional[str]): Filter by category.
            have (Optional[bool]): Filter by have status.
            limit (Optional[int]): Limit results.
            offset (Optional[int]): Offset for pagination.

        Returns:
            List[ShoppingItem]: Filtered shopping items belonging to the user.
        """
        effective_user_id = user_id if user_id is not None else self.user_id
        stmt = select(ShoppingItem).where(ShoppingItem.user_id == effective_user_id)

        # apply filters
        filters = []
        if search_term:
            filters.append(ShoppingItem.ingredient_name.ilike(f"%{search_term}%"))
        if source:
            filters.append(ShoppingItem.source == source)
        if category:
            filters.append(ShoppingItem.category == category)
        if have is not None:
            filters.append(ShoppingItem.have == have)

        if filters:
            stmt = stmt.where(and_(*filters))

        if offset:
            stmt = stmt.offset(offset)
        # Cap results when no explicit limit is given (see MAX_LIST_ROWS).
        stmt = stmt.limit(limit or MAX_LIST_ROWS)

        result = self.session.execute(stmt)
        return result.scalars().all()

    # ── Utility Methods ─────────────────────────────────────────────────────────────────────────────────────
    def get_shopping_list_summary(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary statistics for the shopping list using SQL COUNT for a specific user.

        Args:
            user_id (Optional[int]): ID of the user whose summary to retrieve. Defaults to self.user_id.

        Returns:
            Dict[str, Any]: Summary with counts and categories.
        """
        effective_user_id = user_id if user_id is not None else self.user_id
        # Single query with conditional counts - no loading of all items
        stmt = (
            select(
                func.count(ShoppingItem.id).label('total'),
                func.count(case((ShoppingItem.have == True, 1))).label('checked'),
                func.count(case((ShoppingItem.source == 'recipe', 1))).label('recipe'),
                func.count(case((ShoppingItem.source == 'manual', 1))).label('manual')
            )
            .where(ShoppingItem.user_id == effective_user_id)
        )
        result = self.session.execute(stmt).one()

        # Get distinct categories separately (simple indexed query)
        cat_stmt = (
            select(ShoppingItem.category)
            .distinct()
            .where(ShoppingItem.user_id == effective_user_id)
            .where(ShoppingItem.category.isnot(None))
        )
        categories = sorted([row[0] for row in self.session.execute(cat_stmt)])

        total = result.total or 0
        checked = result.checked or 0

        return {
            "total_items": total,
            "checked_items": checked,
            "recipe_items": result.recipe or 0,
            "manual_items": result.manual or 0,
            "categories": categories,
            "completion_percentage": (checked / total * 100) if total > 0 else 0
        }

    def bulk_update_have_status(self, updates: List[Tuple[int, bool]], user_id: Optional[int] = None) -> int:
        """
        Bulk update have status for multiple items belonging to a user.

        Note: This method needs access to get_shopping_item_by_id from ShoppingItemRepo.
        In practice, this should be called from the service layer which has access to both repos.

        Args:
            updates (List[Tuple[int, bool]]): List of (item_id, have_status) tuples.
            user_id (Optional[int]): ID of the user whose items to update. Defaults to self.user_id.

        Returns:
            int: Number of items updated.
        """
        effective_user_id = user_id if user_id is not None else self.user_id
        updated_count = 0
        for item_id, have_status in updates:
            # Query the item directly to avoid circular dependency
            stmt = select(ShoppingItem).where(
                ShoppingItem.id == item_id,
                ShoppingItem.user_id == effective_user_id
            )
            result = self.session.execute(stmt)
            item = result.scalar_one_or_none()

            if item:
                item.have = have_status
                updated_count += 1

        return updated_count

    def get_recipe_names_for_item(self, item_id: int) -> List[str]:
        """
        Get recipe names that contribute to a shopping item.

        Args:
            item_id: ID of the shopping item

        Returns:
            List of recipe names
        """
        stmt = select(Recipe.recipe_name).distinct().join(
            ShoppingItemContribution,
            ShoppingItemContribution.recipe_id == Recipe.id
        ).where(
            ShoppingItemContribution.shopping_item_id == item_id
        )
        result = self.session.execute(stmt)
        return sorted([row[0] for row in result])
