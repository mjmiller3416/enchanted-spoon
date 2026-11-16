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
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.services.usage_service import UsageLimitExceededError, UsageService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatUsageLedger:
    """Who to charge for billed calls after the first one in this request.

    ``open_charges`` holds units reserved for a call that has not yet
    succeeded and has not yet been refunded. A request-level failure
    releases only this list, so a call that already succeeded is kept
    and a unit already refunded is not released again.
    """

    session: Session
    user_id: int
    field: str
    limit: Optional[int]
    window: Optional[str]
    open_charges: list[UsageService] = field(default_factory=list)


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
    ledger.open_charges.append(service)
    return service


def _take_open_charge(ledger: ChatUsageLedger, service: UsageService) -> bool:
    """Drop one open charge. False when it was already kept or refunded."""
    try:
        ledger.open_charges.remove(service)
    except ValueError:
        return False
    return True


def keep_additional_billed_call(service: Optional[UsageService]) -> None:
    """The provider call succeeded. Leave its unit charged."""
    ledger = _ledger.get()
    if service is None or ledger is None:
        return
    _take_open_charge(ledger, service)


def release_additional_billed_call(service: Optional[UsageService]) -> None:
    """Refund one unit reserved by ``charge_additional_billed_call``.

    A second call for the same unit does nothing, so a local refund and the
    request-level refund cannot both decrement it.
    """
    ledger = _ledger.get()
    if service is None or ledger is None:
        return
    if not _take_open_charge(ledger, service):
        return
    try:
        service.release(ledger.field)
    except Exception:
        logger.exception(
            "Failed to refund an additional chat model call for user %s",
            ledger.user_id,
        )


def release_open_additional_billed_calls() -> None:
    """Refund every extra unit whose call did not succeed.

    Clears the open list first so a second call, including one from the
    request error handler after a local refund, does not decrement again.
    """
    ledger = _ledger.get()
    if ledger is None or not ledger.open_charges:
        return
    pending = list(ledger.open_charges)
    ledger.open_charges.clear()
    for service in pending:
        try:
            service.release(ledger.field)
        except Exception:
            logger.exception(
                "Failed to refund an additional chat model call for user %s",
                ledger.user_id,
            )
