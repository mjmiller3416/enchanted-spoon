"""Optional pictures reserve the same photo allowance as the explicit photo route."""

import logging
from sqlalchemy.orm import Session

from app.core.usage_limits import get_user_monthly_limit
from app.models.user import User
from app.services.usage_service import UsageService, UsageLimitExceededError
from app.services.ai.image_generation import get_image_generation_service

logger = logging.getLogger(__name__)


async def generate_optional_recipe_images(
    session: Session, user: User, recipe_name: str
) -> tuple[str | None, str | None]:
    """Reserve one photo set before spending; preserve the recipe on any failure.

    A set is a reference and banner pair, matching the explicit image route.
    Partial success consumes one unit. A fully failed attempt refunds the unit;
    provider costs for failures/retries still need separate invoice monitoring.
    Reservation errors fail closed: no provider call is made.
    """
    usage = UsageService(session, user.id)
    limit = None if user.is_admin else get_user_monthly_limit(user, "ai_images_generated")
    try:
        usage.reserve("ai_images_generated", limit)
    except UsageLimitExceededError:
        return None, None
    except Exception:
        session.rollback()
        logger.warning("Optional photo reservation failed")
        return None, None

    try:
        result = await get_image_generation_service().generate_dual_recipe_images(recipe_name)
        reference = result.get("reference_image_data")
        banner = result.get("banner_image_data")
        if reference or banner:
            return reference, banner
    except Exception:
        logger.warning("Optional photo generation failed")
    try:
        usage.release("ai_images_generated")
    except Exception:
        session.rollback()
        logger.warning("Optional photo refund failed")
    return None, None
