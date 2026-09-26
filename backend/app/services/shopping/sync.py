"""app/services/shopping/sync.py

Planner sync logic mixin for shopping service.
Handles diff-based synchronization between planner state and shopping list.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

from ...dtos.shopping_dtos import (
    ShoppingListGenerationDTO,
    ShoppingListGenerationResultDTO,
)
from ...models.shopping_item import ShoppingItem
from ...models.shopping_item_contribution import ShoppingItemContribution
from ...services.unit_conversion_service import UnitConversionService
from ...utils.unit_conversion import to_display_unit


# -- Sync Mixin ----------------------------------------------------------------------------------
class SyncMixin:
    """Mixin providing planner synchronization methods."""

    # -- Core Sync Method ------------------------------------------------------------------------
    def sync_shopping_list(self) -> Dict[str, int]:
        """
        Synchronize shopping list with current planner state using diff-based algorithm.

        This is the core method that should be called after ANY planner mutation.
        It compares desired state (from active planner entries) with current state
        and applies minimal updates.

        Returns:
            Dict with counts: items_created, items_updated, items_deleted, contributions_synced
        """
        try:
            # 1. Get active planner entries (not completed, not cleared, shopping_mode != 'none')
            active_entries = self.planner_repo.get_shopping_entries(self.user_id)

            # 2. Calculate desired contributions from all active entries
            # Structure: {aggregation_key: {(entry_id, recipe_id): {base_qty, dimension, category, name}}}
            desired_contributions: Dict[str, Dict[tuple, Dict[str, Any]]] = (
                defaultdict(dict)
            )

            conversion_service = UnitConversionService(self.session, self.user_id)

            for entry in active_entries:
                if not entry.meal:
                    continue

                recipe_ids = entry.meal.get_all_recipe_ids()
                category_filter = (
                    "produce" if entry.shopping_mode == "produce_only" else None
                )

                # Get contributions for this entry
                entry_contributions = (
                    self.shopping_repo.aggregate_ingredients_for_entry(
                        recipe_ids, entry.id, category_filter
                    )
                )

                # Merge into desired state
                for agg_key, contrib_list in entry_contributions.items():
                    for contrib in contrib_list:
                        key = (entry.id, contrib.recipe_id)
                        if key not in desired_contributions[agg_key]:
                            desired_contributions[agg_key][key] = {
                                "base_quantity": 0.0,
                                "dimension": contrib.dimension,
                                "planner_entry_id": entry.id,
                                "recipe_id": contrib.recipe_id,
                                "original_unit": contrib.original_unit,
                                "category": contrib.category,
                            }
                        desired_contributions[agg_key][key][
                            "base_quantity"
                        ] += contrib.base_quantity
                        # Keep track of original_unit (prefer non-None)
                        if contrib.original_unit and not desired_contributions[
                            agg_key
                        ][key].get("original_unit"):
                            desired_contributions[agg_key][key][
                                "original_unit"
                            ] = contrib.original_unit

            # 3. Get current recipe items from database
            current_items = self.shopping_repo.get_items_by_aggregation_keys(
                list(desired_contributions.keys())
            )

            # Also get any recipe items that might be orphaned (not in desired state)
            all_recipe_items = {
                item.aggregation_key: item
                for item in self.shopping_repo.get_all_shopping_items(source="recipe")
                if item.aggregation_key
            }

            stats = {
                "items_created": 0,
                "items_updated": 0,
                "items_deleted": 0,
                "contributions_synced": 0,
            }

            # Contribution rewrites are collected across the loop and applied in
            # two bulk statements (delete + insert) instead of per-item round trips
            items_to_clear: List[int] = []
            pending_contributions: List[ShoppingItemContribution] = []

            # 4. Process each desired aggregation key
            for agg_key, contributions in desired_contributions.items():
                # Calculate total base quantity
                total_base_qty = sum(c["base_quantity"] for c in contributions.values())

                # Get sample contribution for metadata
                sample_contrib = next(iter(contributions.values()))
                dimension = sample_contrib["dimension"]

                # Find the first non-None original_unit from all contributions
                original_unit = None
                for contrib_data in contributions.values():
                    if contrib_data.get("original_unit"):
                        original_unit = contrib_data["original_unit"]
                        break

                # Get ingredient info from the aggregation key
                parts = agg_key.split("::")
                ingredient_name = parts[0] if parts else "Unknown"

                # Read category from the contribution data (already fetched via FK join)
                category = sample_contrib.get("category")

                # Calculate display quantity (pass original_unit for unit preservation)
                display_qty, display_unit = to_display_unit(
                    total_base_qty, dimension, original_unit
                )

                # Apply ingredient-specific conversion rules
                display_qty, display_unit = conversion_service.apply_conversion(
                    ingredient_name, display_qty, display_unit
                )

                if agg_key in current_items:
                    # Update existing item
                    item = current_items[agg_key]
                    old_qty = item.quantity

                    # Update quantity and unit
                    item.quantity = display_qty
                    item.unit = display_unit[:50] if display_unit else display_unit

                    # If quantity INCREASED, uncheck (user needs to collect more)
                    if display_qty > old_qty + 0.01:
                        item.have = False

                    # Existing contributions are cleared in bulk after the loop
                    items_to_clear.append(item.id)
                    stats["items_updated"] += 1
                else:
                    # Create new item
                    # Clamp to the column sizes: recipe ingredient text is
                    # unbounded, and one oversize value would fail every sync
                    item = ShoppingItem.create_from_recipe(
                        ingredient_name=ingredient_name.capitalize()[:255],
                        quantity=display_qty,
                        unit=display_unit[:50] if display_unit else display_unit,
                        category=category[:100] if category else category,
                        aggregation_key=agg_key.lower().strip(),
                    )
                    self.shopping_repo.create_shopping_item(item)
                    stats["items_created"] += 1

                pending_contributions.extend(
                    self._build_contributions(item, contributions)
                )
                stats["contributions_synced"] += len(contributions)

                # Remove from all_recipe_items so we know it's not orphaned
                if agg_key in all_recipe_items:
                    del all_recipe_items[agg_key]

            # 5. Apply collected contribution rewrites in bulk
            # (delete must run before the inserts flush so replaced rows are gone first)
            self.shopping_repo.delete_contributions_for_items(items_to_clear)
            self.shopping_repo.add_contributions(pending_contributions)

            # 6. Delete orphaned items (items no longer in desired state)
            for agg_key, item in all_recipe_items.items():
                if agg_key not in desired_contributions:
                    self.shopping_repo.delete_item(item.id)
                    stats["items_deleted"] += 1

            logger.debug(f"Sync complete - stats: {stats}")
            self.session.commit()
            return stats

        except SQLAlchemyError as e:
            logger.error(f"Shopping sync SQLAlchemyError: {type(e).__name__}: {e}")
            logger.error(f"Error details: {e.args}")
            self.session.rollback()
            raise RuntimeError(f"Failed to sync shopping list: {e}") from e

    def _build_contributions(
        self, item: ShoppingItem, desired_contributions: Dict[tuple, Dict[str, Any]]
    ) -> List[ShoppingItemContribution]:
        """
        Build the desired contribution rows for a single shopping item.
        Rows are persisted in bulk by the caller.

        Args:
            item: The shopping item the contributions belong to
            desired_contributions: Dict of (entry_id, recipe_id) -> contribution data

        Returns:
            Unpersisted ShoppingItemContribution instances
        """
        return [
            ShoppingItemContribution(
                shopping_item_id=item.id,
                recipe_id=recipe_id,
                planner_entry_id=entry_id,
                base_quantity=data["base_quantity"],
                dimension=data["dimension"],
            )
            for (entry_id, recipe_id), data in desired_contributions.items()
        ]

    # -- Generate Methods (for API compatibility) ------------------------------------------------
    def generate_shopping_list(
        self, generation_dto: ShoppingListGenerationDTO
    ) -> ShoppingListGenerationResultDTO:
        """
        Generate shopping list from recipe IDs.
        This now uses the sync mechanism internally.

        Args:
            generation_dto: DTO with recipe_ids to generate from.

        Returns:
            ShoppingListGenerationResultDTO with operation statistics.
        """
        # For now, this method is kept for API compatibility but uses sync internally
        try:
            stats = self.sync_shopping_list()
            total_items = len(self.shopping_repo.get_all_shopping_items())
            return ShoppingListGenerationResultDTO(
                success=True,
                items_created=stats["items_created"],
                items_updated=stats["items_updated"],
                total_items=total_items,
                message=f"Synced shopping list: {stats['items_created']} created, {stats['items_updated']} updated, {stats['items_deleted']} deleted",
            )
        except Exception as e:
            return ShoppingListGenerationResultDTO(
                success=False,
                items_created=0,
                items_updated=0,
                total_items=0,
                message=str(e),
                errors=[str(e)],
            )

    def generate_from_active_planner(self) -> ShoppingListGenerationResultDTO:
        """
        Generate shopping list from active planner entries.
        This method now just calls sync_shopping_list() for backwards compatibility.
        """
        try:
            stats = self.sync_shopping_list()
            total_items = len(self.shopping_repo.get_all_shopping_items())
            return ShoppingListGenerationResultDTO(
                success=True,
                items_created=stats["items_created"],
                items_updated=stats["items_updated"],
                total_items=total_items,
                message=f"Synced shopping list: {stats['items_created']} created, {stats['items_updated']} updated, {stats['items_deleted']} deleted",
            )
        except Exception as e:
            return ShoppingListGenerationResultDTO(
                success=False,
                items_created=0,
                items_updated=0,
                total_items=0,
                message=str(e),
                errors=[str(e)],
            )
