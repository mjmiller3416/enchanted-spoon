"""app/services/shopping

Modular shopping service package.
Combines core service, item management, planner sync, and aggregation.
"""

from .aggregation import AggregationMixin
from .item import ItemManagementMixin
from .notes import NotesMixin
from .service import ShoppingServiceCore
from .sync import SyncMixin


# ── Unified Service ─────────────────────────────────────────────────────────────────────────────
class ShoppingService(
    AggregationMixin, ItemManagementMixin, NotesMixin, SyncMixin, ShoppingServiceCore
):
    """Unified shopping service combining all functionality.

    Inherits from:
    - ShoppingServiceCore: Initialization, list retrieval, helpers, summary
    - SyncMixin: Planner synchronization and generation methods
    - ItemManagementMixin: Item CRUD and status management
    - AggregationMixin: Ingredient breakdown and analysis
    - NotesMixin: Free-text shopping list notes
    """

    pass


__all__ = [
    "ShoppingService",
]
