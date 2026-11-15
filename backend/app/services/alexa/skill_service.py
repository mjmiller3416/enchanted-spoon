"""app/services/alexa/skill_service.py

What the Enchanted Spoon Alexa skill says and does, given a verified request.

    "Alexa, tell Enchanted Spoon to add a gallon of milk"
    "Alexa, ask Enchanted Spoon what's on my shopping list"

The access token comes from Alexa account linking (OAuth scope ``alexa``,
see ``oauth_service.granted_scope``) and maps to the account that linked.
Writes go to that person's kitchen (the household owner's list when they
are a member), through ``ShoppingService.add_named_item``: the same deduped,
library-categorised add the Hearth wall uses. Read-only accounts can read
the list but not add to it, as in the app.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...core.mcp_config import ALEXA_SCOPE
from ...dtos.shopping_dtos import ManualItemCreateDTO
from ...models.user import User
from ...repositories.ingredient_repo import IngredientRepo
from ...utils.spoken_items import SpokenItem, parse_spoken_items
from ..household.scope import kitchen_user_id
from ..oauth_service import OAuthService
from ..shopping import ShoppingService
from ..user_service import UserService

logger = logging.getLogger(__name__)

ADD_INTENT = "AddItemIntent"
READ_INTENT = "ReadListIntent"
ITEM_SLOT = "item"
MAX_ITEMS_PER_REQUEST = 10
MAX_ITEMS_READ = 10

HELP_TEXT = (
    "You can say, add a gallon of milk, or add eggs and bread. "
    "To hear your list, say, what's on my shopping list. What would you like to add?"
)
LAUNCH_TEXT = "What should I add to your shopping list?"
REPROMPT_TEXT = "Say something like, add a gallon of milk."
LINK_TEXT = (
    "To add to your Enchanted Spoon shopping list, link your account first. "
    "I've sent a card to the Alexa app to get you started."
)
READ_ONLY_TEXT = (
    "Your Enchanted Spoon account is read only right now, so I can't add to the list. "
    "Open the app to pick a plan."
)
FAILED_TEXT = "Sorry, I couldn't reach your shopping list just now. Please try again in a minute."


# ── Response building ───────────────────────────────────────────────────────
def build_response(
    text: Optional[str] = None,
    *,
    end_session: bool = True,
    reprompt: Optional[str] = None,
    link_account: bool = False,
    card_title: Optional[str] = None,
) -> Dict[str, Any]:
    """An Alexa response envelope with plain-text speech."""
    response: Dict[str, Any] = {}
    if text is not None:
        response["outputSpeech"] = {"type": "PlainText", "text": text}
    if reprompt:
        response["reprompt"] = {"outputSpeech": {"type": "PlainText", "text": reprompt}}
    if link_account:
        response["card"] = {"type": "LinkAccount"}
    elif card_title and text:
        response["card"] = {"type": "Simple", "title": card_title, "content": text}
    if text is not None or reprompt:
        response["shouldEndSession"] = end_session
    return {"version": "1.0", "response": response}


def _ask(text: str, reprompt: str = REPROMPT_TEXT) -> Dict[str, Any]:
    return build_response(text, end_session=False, reprompt=reprompt)


def join_words(words: List[str]) -> str:
    """"milk", "milk and eggs", "milk, eggs and bread"."""
    if len(words) <= 1:
        return "".join(words)
    return f"{', '.join(words[:-1])} and {words[-1]}"


def access_token(envelope: Dict[str, Any]) -> Optional[str]:
    """The linked account's token, if the person has linked."""
    system_user = (((envelope.get("context") or {}).get("System") or {}).get("user") or {})
    session_user = ((envelope.get("session") or {}).get("user") or {})
    token = system_user.get("accessToken") or session_user.get("accessToken")
    return token if isinstance(token, str) and token else None


def slot_value(intent: Dict[str, Any], name: str) -> Optional[str]:
    slot = (intent.get("slots") or {}).get(name) or {}
    value = slot.get("value")
    return value.strip() if isinstance(value, str) and value.strip() else None


class AlexaSkillService:
    """Answers one Alexa request (already verified as Alexa's, for our skill)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Entry point ─────────────────────────────────────────────────────────
    def handle(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """The response for a request envelope."""
        request = envelope.get("request") or {}
        kind = request.get("type")
        if kind == "SessionEndedRequest":
            return build_response()
        if kind == "LaunchRequest":
            if self._linked_user(envelope) is None:
                return build_response(LINK_TEXT, link_account=True)
            return _ask(LAUNCH_TEXT)
        if kind != "IntentRequest":
            return build_response()

        intent = request.get("intent") or {}
        name = intent.get("name")
        if name in ("AMAZON.StopIntent", "AMAZON.CancelIntent", "AMAZON.NavigateHomeIntent"):
            return build_response("Okay.")
        if name == "AMAZON.HelpIntent":
            return _ask(HELP_TEXT)
        if name == "AMAZON.FallbackIntent":
            return _ask("Sorry, I didn't catch that. " + HELP_TEXT)

        user = self._linked_user(envelope)
        if user is None:
            return build_response(LINK_TEXT, link_account=True)
        if name == ADD_INTENT:
            return self.add_items(user, slot_value(intent, ITEM_SLOT))
        if name == READ_INTENT:
            return self.read_list(user)
        return _ask("Sorry, I can't do that yet. " + HELP_TEXT)

    def _linked_user(self, envelope: Dict[str, Any]) -> Optional[User]:
        """The account behind the linked token; None when unlinked, expired or revoked."""
        token = access_token(envelope)
        if token is None:
            return None
        user_id = OAuthService(self.session).user_for_access_token(token, ALEXA_SCOPE)
        if user_id is None:
            return None
        user = UserService(self.session).get_by_id(user_id)
        if user is not None:
            UserService(self.session).touch_last_active(user)
        return user

    # ── Intents ─────────────────────────────────────────────────────────────
    def add_items(self, user: User, phrase: Optional[str]) -> Dict[str, Any]:
        """Add what was said to the person's kitchen shopping list and say what happened."""
        if user.is_read_only is True:
            return build_response(READ_ONLY_TEXT)
        kitchen = kitchen_user_id(self.session, user)
        library = IngredientRepo(self.session, kitchen)

        def is_known(name: str) -> bool:
            try:
                return library.find_category_by_names([name]) is not None
            except SQLAlchemyError:
                self.session.rollback()
                return False

        items = parse_spoken_items(phrase, is_known)[:MAX_ITEMS_PER_REQUEST]
        if not items:
            return _ask("What should I add?", "Say the item, like, add a gallon of milk.")

        service = ShoppingService(self.session, kitchen)
        added: List[str] = []
        already: List[str] = []
        failed: List[str] = []
        for item in items:
            result = service.add_named_item(self._create_dto(item))
            if result is None:
                failed.append(item.name)
            elif result.added or result.reactivated:
                added.append(item.spoken)
            else:
                already.append(result.already_listed[0] if result.already_listed else item.name)
        logger.info(
            "alexa add for user %s: %s added, %s already listed, %s failed",
            user.id, len(added), len(already), len(failed),
        )
        if failed and not added and not already:
            return build_response(FAILED_TEXT)

        sentences: List[str] = []
        if added:
            sentences.append(f"Added {join_words(added)} to your shopping list.")
        if already:
            verb = "is" if len(already) == 1 else "are"
            sentences.append(f"{join_words(already).capitalize()} {verb} already on your list.")
        if failed:
            sentences.append(f"I couldn't add {join_words(failed)}. Please try again.")
        text = " ".join(sentences)
        return build_response(text, card_title="Shopping list")

    @staticmethod
    def _create_dto(item: SpokenItem) -> ManualItemCreateDTO:
        return ManualItemCreateDTO(ingredient_name=item.name, quantity=item.quantity, unit=item.unit)

    def read_list(self, user: User) -> Dict[str, Any]:
        """Read out what's still needed on the person's kitchen shopping list."""
        try:
            listing = ShoppingService(self.session, kitchen_user_id(self.session, user)).get_shopping_list()
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("alexa read failed for user %s", user.id)
            return build_response(FAILED_TEXT)
        needed: List[str] = []
        seen: set[str] = set()
        for row in listing.items:
            key = row.ingredient_name.strip().lower()
            if row.have or key in seen:
                continue
            seen.add(key)
            needed.append(row.ingredient_name.strip())
        if not needed:
            return build_response("Your shopping list is empty.")
        spoken = needed[:MAX_ITEMS_READ]
        extra = len(needed) - len(spoken)
        count = f"{len(needed)} thing" + ("" if len(needed) == 1 else "s")
        names = join_words(spoken + ([f"{extra} more"] if extra else []))
        return build_response(f"You have {count} on your shopping list: {names}.", card_title="Shopping list")
