"""app/repositories/shopping

Shopping repository package with modular structure.
Provides item operations, aggregation, and contribution management.
"""

from sqlalchemy.orm import Session

from .aggregation_repo import (
    AggregatedIngredient,
    ContributionData,
    ShoppingAggregationRepo,
)
from .contribution_repo import ShoppingContributionRepo
from .item_repo import ShoppingItemRepo
from .note_repo import ShoppingNoteRepo


class ShoppingRepo:
    """Unified shopping repository that delegates to specialized sub-repositories.

    Provides backwards compatibility while maintaining modular structure.
    """

    def __init__(self, session: Session, user_id: int):
        """Initialize the unified Shopping Repository.

        Args:
            session: SQLAlchemy database session
            user_id: The ID of the current user for multi-tenant isolation
        """
        self.session = session
        self.user_id = user_id

        # Initialize sub-repositories
        self.item_repo = ShoppingItemRepo(session, user_id)
        self.aggregation_repo = ShoppingAggregationRepo(session, user_id)
        self.contribution_repo = ShoppingContributionRepo(session, user_id)
        self.note_repo = ShoppingNoteRepo(session, user_id)

    # ── Item Operations (delegate to item_repo) ─────────────────────────────────────────────────────────────
    def create_shopping_item(self, shopping_item, user_id=None):
        """Create a new shopping item."""
        return self.item_repo.create_shopping_item(shopping_item, user_id)

    def add_manual_item(self, shopping_item, user_id):
        """Add a manual shopping item."""
        return self.item_repo.add_manual_item(shopping_item, user_id)

    def get_shopping_item_by_id(self, item_id, user_id=None):
        """Get shopping item by ID."""
        return self.item_repo.get_shopping_item_by_id(item_id, user_id)

    def get_shopping_item_by_aggregation_key(self, aggregation_key):
        """Get shopping item by aggregation key."""
        return self.item_repo.get_shopping_item_by_aggregation_key(aggregation_key)

    def get_recipe_items_with_contributions(self):
        """Get recipe items with contributions loaded."""
        return self.item_repo.get_recipe_items_with_contributions()

    def get_items_by_aggregation_keys(self, keys):
        """Get multiple items by aggregation keys."""
        return self.item_repo.get_items_by_aggregation_keys(keys)

    def update_item_status(self, item_id, have, user_id=None):
        """Update item have status."""
        return self.item_repo.update_item_status(item_id, have, user_id)

    def get_all_shopping_items(self, user_id=None, source=None):
        """Get all shopping items for user."""
        return self.item_repo.get_all_shopping_items(user_id, source)

    def update_item(self, shopping_item):
        """Update an existing shopping item."""
        return self.item_repo.update_item(shopping_item)

    def delete_item(self, item_id, user_id=None):
        """Delete a shopping item."""
        return self.item_repo.delete_item(item_id, user_id)

    def clear_shopping_items(self, user_id=None, source=None):
        """Clear shopping items."""
        return self.item_repo.clear_shopping_items(user_id, source)

    def clear_recipe_items(self, user_id=None):
        """Clear recipe items."""
        return self.item_repo.clear_recipe_items(user_id)

    # ── Note Operations (delegate to note_repo) ──────────────────────────────────────────────────────────────
    def get_note(self):
        """Get the user's shopping notes."""
        return self.note_repo.get_note()

    def upsert_note(self, content):
        """Create or replace the user's shopping notes."""
        return self.note_repo.upsert_note(content)

    # ── Aggregation Operations (delegate to aggregation_repo) ──────────────────────────────────────────────
    def get_recipe_ingredients(self, recipe_ids):
        """Get recipe ingredients."""
        return self.aggregation_repo.get_recipe_ingredients(recipe_ids)

    def aggregate_ingredients_for_entry(self, recipe_ids, planner_entry_id, category_filter=None):
        """Aggregate ingredients for a planner entry."""
        return self.aggregation_repo.aggregate_ingredients_for_entry(
            recipe_ids, planner_entry_id, category_filter
        )

    def aggregate_ingredients(self, recipe_ids, category_filter=None):
        """Aggregate ingredients from recipes."""
        return self.aggregation_repo.aggregate_ingredients(recipe_ids, category_filter)

    def get_ingredient_breakdown(self, recipe_ids):
        """Get ingredient breakdown."""
        return self.aggregation_repo.get_ingredient_breakdown(recipe_ids)

    def search_shopping_items(self, user_id=None, search_term=None, source=None,
                              category=None, have=None, limit=None, offset=None):
        """Search shopping items."""
        return self.aggregation_repo.search_shopping_items(
            user_id, search_term, source, category, have, limit, offset
        )

    def get_shopping_list_summary(self, user_id=None):
        """Get shopping list summary."""
        return self.aggregation_repo.get_shopping_list_summary(user_id)

    def bulk_update_have_status(self, updates, user_id=None):
        """Bulk update have status."""
        return self.aggregation_repo.bulk_update_have_status(updates, user_id)

    def get_recipe_names_for_item(self, item_id):
        """Get recipe names for item."""
        return self.aggregation_repo.get_recipe_names_for_item(item_id)

    # ── Contribution Operations (delegate to contribution_repo) ────────────────────────────────────────────
    def add_contribution(self, shopping_item_id, recipe_id, planner_entry_id,
                        base_quantity, dimension):
        """Add a contribution."""
        return self.contribution_repo.add_contribution(
            shopping_item_id, recipe_id, planner_entry_id, base_quantity, dimension
        )

    def delete_contributions_for_entry(self, planner_entry_id):
        """Delete contributions for entry."""
        return self.contribution_repo.delete_contributions_for_entry(planner_entry_id)

    def delete_contributions_for_item(self, shopping_item_id):
        """Delete contributions for item."""
        return self.contribution_repo.delete_contributions_for_item(shopping_item_id)

    def add_contributions(self, contributions):
        """Add multiple contributions in a single flush."""
        return self.contribution_repo.add_contributions(contributions)

    def delete_contributions_for_items(self, shopping_item_ids):
        """Delete contributions for multiple items in one statement."""
        return self.contribution_repo.delete_contributions_for_items(shopping_item_ids)

    def get_contributions_by_entry(self, planner_entry_id):
        """Get contributions by entry."""
        return self.contribution_repo.get_contributions_by_entry(planner_entry_id)

    def get_items_without_contributions(self):
        """Get items without contributions."""
        return self.contribution_repo.get_items_without_contributions()

    def delete_orphaned_recipe_items(self):
        """Delete orphaned recipe items."""
        return self.contribution_repo.delete_orphaned_recipe_items()


__all__ = [
    # Unified repository (backwards compatible)
    "ShoppingRepo",
    # Individual repositories (for direct use if needed)
    "ShoppingItemRepo",
    "ShoppingAggregationRepo",
    "ShoppingContributionRepo",
    "ShoppingNoteRepo",
    # Data classes
    "AggregatedIngredient",
    "ContributionData",
]
