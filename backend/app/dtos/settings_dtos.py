"""Versioned settings contract, including migration of legacy JSON values."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SettingsSection(BaseModel):
    model_config = ConfigDict(extra="allow")


class ProfileSettings(SettingsSection):
    userName: str = "User"
    email: str = ""
    avatar: str = ""


class AppearanceSettings(SettingsSection):
    theme: Literal["light", "dark", "system"] = "dark"


class RecipePreferences(SettingsSection):
    defaultSortOrder: Literal["alphabetical", "recent", "cookTime"] = "alphabetical"
    quickFilters: list[str] = Field(default_factory=lambda: ["breakfast", "lunch", "dinner", "sides", "new"])


class ShoppingSettings(SettingsSection):
    categorySortOrder: Literal["alphabetical", "custom"] = "alphabetical"
    customCategoryOrder: list[str] = Field(default_factory=lambda: ["Produce", "Bakery", "Deli", "Dairy", "Meat", "Seafood", "Frozen", "Pantry", "Condiments", "Oils and Vinegars", "Spices", "Baking", "Beverages", "Other"])
    autoClearChecked: Literal["manual"] = "manual"
    hideCompleted: bool = False

    @model_validator(mode="before")
    @classmethod
    def migrate_clearing(cls, value: Any) -> Any:
        """Unsupported historical choices never performed automatic clearing."""
        if isinstance(value, dict) and value.get("autoClearChecked") in ("daily", "onRefresh"):
            return {**value, "autoClearChecked": "manual"}
        return value


class AISettings(SettingsSection):
    imageGenerationPrompt: str = "A professional cookbook-quality food photograph of {recipe_name}. Style the scene — surface, props, lighting, and camera angle — to match the character of this specific dish. Vary the composition naturally: choose whichever angle, surface, and props a professional food stylist would select for this recipe. Shallow depth of field, natural light, appetizing presentation, high detail, no people, no hands, no text, square format."
    showAssistantFab: bool = True


class InstallPromptSettings(SettingsSection):
    """Install-app prompt bookkeeping, synced so an iOS home-screen launch can silence Safari."""
    installedAt: str | None = None
    dismissCount: int = Field(default=0, ge=0)
    snoozedUntil: str | None = None


class WhatsNewSettings(SettingsSection):
    """"What's new" bookkeeping, synced so every device agrees on what was read."""
    lastSeenRelease: str | None = None
    dismissedSpotlights: list[str] = Field(default_factory=list)


class SettingsDTO(SettingsSection):
    schemaVersion: Literal[1] = 1
    profile: ProfileSettings = Field(default_factory=ProfileSettings)
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)
    recipePreferences: RecipePreferences = Field(default_factory=RecipePreferences)
    shoppingList: ShoppingSettings = Field(default_factory=ShoppingSettings)
    aiFeatures: AISettings = Field(default_factory=AISettings)
    installPrompt: InstallPromptSettings = Field(default_factory=InstallPromptSettings)
    whatsNew: WhatsNewSettings = Field(default_factory=WhatsNewSettings)

    @model_validator(mode="before")
    @classmethod
    def migrate_theme(cls, value: Any) -> Any:
        """Nested values take precedence over the old flat theme field."""
        if isinstance(value, dict) and "appearance" not in value and value.get("theme") in ("light", "dark", "system"):
            return {**value, "appearance": {"theme": value["theme"]}}
        return value
