"""Count every billed model call in one chat turn.

``require_within_usage_limit`` reserves the first call before the handler
runs. A tool follow-up, a meal-planning call, or a recipe-generation retry
is a second (or later) billed call and reserves one more unit here. The
same user, field, limit, and window are used, so the unit lands on the row
the first call already charged and cannot exceed the cap.

With no ledger bound this is a no-op. Non-chat callers and unit tests that
mock the provider are not charged and do not need a database session.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.services.usage_service import UsageLimitExceededError, UsageService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatUsageLedger:
    """Who to charge for billed calls after the first one in this request."""

    session: Session
    user_id: int
    field: str
    limit: Optional[int]
    window: Optional[str]


_ledger: ContextVar[Optional[ChatUsageLedger]] = ContextVar(
    "chat_usage_ledger", default=None
)


def bind_chat_usage_ledger(ledger: ChatUsageLedger) -> Token:
    """Start charging additional chat model calls on ``ledger``."""
    return _ledger.set(ledger)


def reset_chat_usage_ledger(token: Token) -> None:
    """Drop the ledger bound for this request.

    The dependency exit can run in a copied context under the test client.
    Resetting a token from another context raises ``ValueError``; clearing
    the current context still drops the copy.
    """
    try:
        _ledger.reset(token)
    except ValueError:
        _ledger.set(None)


def charge_additional_billed_call() -> Optional[UsageService]:
    """Reserve one more unit for a follow-up call or a retry.

    Returns the service that reserved the unit so the caller can refund it
    if the provider call raises and the whole request fails. Returns None
    when this request is not a metered chat turn.

    Raises:
        UsageLimitExceededError: The cap is already reached. Callers must
            skip the model call.
    """
    ledger = _ledger.get()
    if ledger is None:
        return None
    service = UsageService(ledger.session, ledger.user_id, window=ledger.window)
    try:
        service.reserve(ledger.field, ledger.limit)
    except UsageLimitExceededError:
        logger.info(
            "skipped additional chat model call; usage cap reached user_id=%s",
            ledger.user_id,
        )
        raise
    return service


def release_additional_billed_call(service: Optional[UsageService]) -> None:
    """Refund one unit reserved by ``charge_additional_billed_call``."""
    ledger = _ledger.get()
    if service is None or ledger is None:
        return
    try:
        service.release(ledger.field)
    except Exception:
        logger.exception(
            "Failed to refund an additional chat model call for user %s",
            ledger.user_id,
        )
