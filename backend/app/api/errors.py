"""app/api/errors.py

Shared helpers for turning unexpected server-side failures into responses.
"""

import logging

from fastapi import HTTPException

logger = logging.getLogger("app.api")

GENERIC_ERROR = "Something went wrong on our end. Please try again."


def internal_error(message: str = GENERIC_ERROR, status_code: int = 500) -> HTTPException:
    """
    Log the exception currently being handled and build a client-safe error.

    Call from inside an ``except`` block. The raw exception text (which can
    carry SQL, parameters, or third-party API details) goes to the logs only;
    the client gets ``message``.
    """
    logger.exception("Unhandled error while serving request")
    return HTTPException(status_code=status_code, detail=message)
