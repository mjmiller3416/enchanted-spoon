"""app/services/shopping/item.py

Item CRUD and status management mixin for shopping service.
Handles manual item creation, updates, deletions, and status toggles.
"""

# -- Imports -------------------------------------------------------------------------------------
from typing import Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ...dtos.shopping_dtos import (
    BulkOperationResultDTO,
    BulkStateUpdateDTO,
    ExternalItemUpsertDTO,
    ManualItemCreateDTO,
    ManualItemsAddResultDTO,
    ShoppingItemResponseDTO,
    ShoppingItemUpdateDTO,
)
from ...models.shopping_item import ShoppingItem


# -- Item Management Mixin -----------------------------------------------------------------------
class ItemManagementMixin:
    """Mixin providing item CRUD and status management methods."""

    # -- Manual Item Management ------------------------------------------------------------------
    def add_manual_item(
        self, create_dto: ManualItemCreateDTO
    ) -> Optional[ShoppingItemResponseDTO]:
        """
        Add a manual item to the shopping list for the current user.

        Args:
            create_dto (ManualItemCreateDTO): Manual item data.

        Returns:
            Optional[ShoppingItemResponseDTO]: Created item or None if failed.
        """
        try:
            manual_item = ShoppingItem.create_manual(
                ingredient_name=create_dto.ingredient_name,
                quantity=create_dto.quantity,
                unit=create_dto.unit,
                category=create_dto.category,
            )

            created_item = self.shopping_repo.create_shopping_item(
                manual_item, self.user_id
            )
            self.session.commit()
            return self._item_to_response_dto(created_item)

        except SQLAlchemyError:
            self.session.rollback()
            return None

    def add_manual_items(
        self, create_dtos: List[ManualItemCreateDTO]
    ) -> Optional[ManualItemsAddResultDTO]:
        """
        Add a batch of manual items, skipping anything already on the list.

        Names match case-insensitively against every item on the list (any source).
        A match still needed is skipped; a match already checked off is moved back
        to "need" instead of being duplicated. The batch commits as one transaction.

        Args:
            create_dtos (List[ManualItemCreateDTO]): Items to add.

        Returns:
            Optional[ManualItemsAddResultDTO]: What was added, reactivated, or
            skipped, or None if the batch failed.
        """
        try:
            # Prefer a still-needed row when several share a name, so a needed
            # match is reported as a duplicate rather than reactivating another
            existing: Dict[str, ShoppingItem] = {}
            for item in self.shopping_repo.get_all_shopping_items(self.user_id):
                key = self._dedupe_key(item.ingredient_name)
                if key not in existing or (existing[key].have and not item.have):
                    existing[key] = item

            added: List[ShoppingItem] = []
            reactivated: List[ShoppingItem] = []
            already_listed: List[str] = []

            for dto in create_dtos:
                key = self._dedupe_key(dto.ingredient_name)
                match = existing.get(key)
                if match is None:
                    created = self.shopping_repo.create_shopping_item(
                        ShoppingItem.create_manual(
                            ingredient_name=dto.ingredient_name,
                            quantity=dto.quantity,
                            unit=dto.unit,
                            category=dto.category,
                        ),
                        self.user_id,
                    )
                    existing[key] = created
                    added.append(created)
                elif match.have:
                    match.have = False
                    self.shopping_repo.update_item(match)
                    reactivated.append(match)
                else:
                    already_listed.append(match.ingredient_name)

            self.session.commit()
            return ManualItemsAddResultDTO(
                added=[self._item_to_response_dto(i) for i in added],
                reactivated=[self._item_to_response_dto(i) for i in reactivated],
                already_listed=already_listed,
            )

        except SQLAlchemyError:
            self.session.rollback()
            return None

    @staticmethod
    def _dedupe_key(name: str) -> str:
        """
        Loose match key so "Eggs" finds "Egg" and "Tomatoes" finds "Tomato".

        Only the trailing plural is folded. Both sides go through the same rules,
        so the key only has to be consistent, not a correct singular.
        """
        key = " ".join(name.lower().split())
        if key.endswith("ies") and len(key) > 4:
            return key[:-3] + "y"
        if key.endswith(("oes", "ches", "shes", "xes")):
            return key[:-2]
        if key.endswith("s") and not key.endswith(("ss", "us")) and len(key) > 3:
            return key[:-1]
        return key

    # -- External Item Ingest --------------------------------------------------------------------
    def upsert_external_item(
        self, upsert_dto: ExternalItemUpsertDTO
    ) -> Optional[Tuple[ShoppingItemResponseDTO, bool]]:
        """
        Upsert an item pushed by a trusted external app for the current user.

        Deduped on (name, source) via the external aggregation key, so repeated
        pushes of the same item update the existing row instead of duplicating it.

        Args:
            upsert_dto (ExternalItemUpsertDTO): Pushed item data.

        Returns:
            Optional[Tuple[ShoppingItemResponseDTO, bool]]: The upserted item and
            a created flag (True = inserted, False = updated), or None if failed.
        """
        aggregation_key = ShoppingItem.make_external_aggregation_key(
            upsert_dto.source, upsert_dto.name
        )
        try:
            existing = self.shopping_repo.get_shopping_item_by_aggregation_key(
                aggregation_key
            )
            if existing:
                return self._apply_external_update(existing, upsert_dto), False

            item = ShoppingItem.create_external(
                ingredient_name=upsert_dto.name,
                source=upsert_dto.source,
                quantity=upsert_dto.quantity if upsert_dto.quantity is not None else 1.0,
                unit=upsert_dto.unit,
                category=upsert_dto.category,
            )
            created_item = self.shopping_repo.create_shopping_item(item, self.user_id)
            self.session.commit()
            return self._item_to_response_dto(created_item), True

        except IntegrityError:
            # Lost a create race against a concurrent push of the same item
            # (unique constraint on aggregation_key + user_id); retry as update
            self.session.rollback()
            existing = self.shopping_repo.get_shopping_item_by_aggregation_key(
                aggregation_key
            )
            if not existing:
                return None
            try:
                return self._apply_external_update(existing, upsert_dto), False
            except SQLAlchemyError:
                self.session.rollback()
                return None

        except SQLAlchemyError:
            self.session.rollback()
            return None

    def _apply_external_update(
        self, item: ShoppingItem, upsert_dto: ExternalItemUpsertDTO
    ) -> ShoppingItemResponseDTO:
        """Apply a re-push to an existing external item and commit."""
        if upsert_dto.quantity is not None:
            item.quantity = upsert_dto.quantity
        if upsert_dto.unit is not None:
            item.unit = upsert_dto.unit
        if upsert_dto.category is not None:
            item.category = upsert_dto.category
        # A re-push means the item is needed again, even if previously checked off
        item.have = False
        self.shopping_repo.update_item(item)
        self.session.commit()
        return self._item_to_response_dto(item)

    def update_item(
        self, item_id: int, update_dto: ShoppingItemUpdateDTO
    ) -> Optional[ShoppingItemResponseDTO]:
        """
        Update a shopping item for the current user.

        Args:
            item_id (int): ID of the item to update.
            update_dto (ShoppingItemUpdateDTO): Update data.

        Returns:
            Optional[ShoppingItemResponseDTO]: Updated item or None if failed/not owned.
        """
        try:
            item = self.shopping_repo.get_shopping_item_by_id(item_id, self.user_id)
            if not item:
                return None

            # update fields from DTO
            if update_dto.ingredient_name is not None:
                item.ingredient_name = update_dto.ingredient_name
            if update_dto.quantity is not None:
                item.quantity = update_dto.quantity
            if update_dto.unit is not None:
                item.unit = update_dto.unit
            if update_dto.category is not None:
                item.category = update_dto.category
            if update_dto.flagged is not None:
                item.flagged = update_dto.flagged
            if update_dto.have is not None:
                item.have = update_dto.have

            updated_item = self.shopping_repo.update_item(item)
            self.session.commit()
            return self._item_to_response_dto(updated_item)

        except SQLAlchemyError:
            self.session.rollback()
            return None

    def delete_item(self, item_id: int) -> bool:
        """
        Delete a shopping item for the current user.

        Args:
            item_id (int): ID of the item to delete.

        Returns:
            bool: True if deleted successfully.
        """
        try:
            result = self.shopping_repo.delete_item(item_id, self.user_id)
            self.session.commit()
            return result
        except SQLAlchemyError:
            self.session.rollback()
            return False

    def clear_manual_items(self) -> BulkOperationResultDTO:
        """
        Clear all manual items from the shopping list for the current user.

        Returns:
            BulkOperationResultDTO: Operation result.
        """
        try:
            deleted_count = self.shopping_repo.clear_shopping_items(
                self.user_id, source="manual"
            )
            self.session.commit()
            return BulkOperationResultDTO(
                success=True,
                updated_count=deleted_count,
                message=f"Cleared {deleted_count} manual items",
            )

        except SQLAlchemyError as e:
            self.session.rollback()
            return BulkOperationResultDTO(
                success=False,
                updated_count=0,
                message="Failed to clear manual items",
                errors=[str(e)],
            )

    def clear_recipe_items(self) -> BulkOperationResultDTO:
        """
        Clear all recipe-generated items from the shopping list for the current user.

        Returns:
            BulkOperationResultDTO: Operation result.
        """
        try:
            deleted_count = self.shopping_repo.clear_shopping_items(
                self.user_id, source="recipe"
            )
            self.session.commit()
            return BulkOperationResultDTO(
                success=True,
                updated_count=deleted_count,
                message=f"Cleared {deleted_count} recipe items",
            )

        except SQLAlchemyError as e:
            self.session.rollback()
            return BulkOperationResultDTO(
                success=False,
                updated_count=0,
                message="Failed to clear recipe items",
                errors=[str(e)],
            )

    # -- Item Status Management ------------------------------------------------------------------
    def toggle_item_status(self, item_id: int) -> Optional[bool]:
        """
        Toggle the 'have' status of a shopping item for the current user.

        Args:
            item_id (int): ID of the item to toggle.

        Returns:
            Optional[bool]: True if successful, None/False if failed.
        """
        try:
            item = self.shopping_repo.get_shopping_item_by_id(item_id, self.user_id)
            if not item:
                return False

            item.have = not item.have
            self.shopping_repo.update_item(item)
            self.session.commit()
            return True

        except SQLAlchemyError:
            self.session.rollback()
            return False

    def toggle_item_flagged(self, item_id: int) -> Optional[bool]:
        """
        Toggle the 'flagged' status of a shopping item for the current user.

        Args:
            item_id (int): ID of the item to toggle.

        Returns:
            Optional[bool]: New flagged status or None if item not found/not owned.
        """
        try:
            item = self.shopping_repo.get_shopping_item_by_id(item_id, self.user_id)
            if not item:
                return None

            item.flagged = not item.flagged
            self.shopping_repo.update_item(item)
            self.session.commit()
            return item.flagged

        except SQLAlchemyError:
            self.session.rollback()
            return None

    def clear_completed_items(self) -> int:
        """
        Clear all completed (have=True) shopping items for the current user and return count deleted.
        """
        from sqlalchemy import delete

        from ...models.shopping_item import ShoppingItem

        try:
            stmt = (
                delete(ShoppingItem)
                .where(ShoppingItem.user_id == self.user_id)
                .where(ShoppingItem.have.is_(True))
            )
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount
        except SQLAlchemyError:
            self.session.rollback()
            return 0

    def bulk_update_status(
        self, update_dto: BulkStateUpdateDTO
    ) -> BulkOperationResultDTO:
        """
        Bulk update 'have' status for multiple shopping items for the current user.

        Args:
            update_dto (BulkStateUpdateDTO): DTO containing item_updates mapping.

        Returns:
            BulkOperationResultDTO: Operation result with count of updated items.
        """
        try:
            updated_count = 0
            for item_id, have in update_dto.item_updates.items():
                item = self.shopping_repo.get_shopping_item_by_id(
                    item_id, self.user_id
                )
                if not item:
                    continue
                item.have = have
                self.shopping_repo.update_item(item)
                updated_count += 1

            self.session.commit()
            return BulkOperationResultDTO(
                success=True,
                updated_count=updated_count,
                message=f"Updated {updated_count} items",
            )
        except SQLAlchemyError as e:
            self.session.rollback()
            return BulkOperationResultDTO(
                success=False,
                updated_count=0,
                message="Failed to bulk update items",
                errors=[str(e)],
            )
