"""app/api/alexa.py

The Enchanted Spoon Alexa skill's HTTPS endpoint.

    POST /api/alexa         the skill's requests (Amazon-signed)
    POST /api/alexa/link    link Alexa by the code it read out (Clerk JWT)

Alexa signs every request; the signature, cert chain, timestamp and skill ID
are checked before anything is read (``services/alexa/verification.py``),
and anything that fails gets a bare 400. With no ``ALEXA_SKILL_ID`` set the
endpoint answers 404. Registered on the public app only (``connector_router``),
like the MCP connector.
"""

import json
import logging
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.alexa_config import ALEXA_PATH, alexa_skill_ids
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.dtos.alexa_dtos import AlexaLinkRequestDTO, AlexaLinkResultDTO
from app.models.user import User
from app.services.alexa import AlexaSkillService, AlexaVerificationError, SignatureVerifier, default_verifier
from app.services.alexa.link_service import AlexaLinkService, AlexaPairingError
from app.services.alexa.verification import check_application, check_timestamp

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_BODY_BYTES = 256 * 1024


def get_verifier() -> SignatureVerifier:
    """The signature verifier (overridable in tests)."""
    return default_verifier()


def _bad_request() -> JSONResponse:
    return JSONResponse({"detail": "Bad Request"}, status_code=400)


@router.post(ALEXA_PATH, include_in_schema=False)
async def alexa_endpoint(
    request: Request,
    session: Session = Depends(get_session),
    verifier: SignatureVerifier = Depends(get_verifier),
) -> JSONResponse:
    """Verify an Alexa request, then answer it."""
    skill_ids = alexa_skill_ids()
    if not skill_ids:
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        return _bad_request()
    verify: Callable[[], None] = lambda: verifier.verify(  # noqa: E731
        request.headers.get("SignatureCertChainUrl"), request.headers.get("Signature-256"), body
    )
    try:
        await run_in_threadpool(verify)
        envelope = json.loads(body)
        if not isinstance(envelope, dict):
            raise AlexaVerificationError("Body is not a JSON object.")
        check_timestamp((envelope.get("request") or {}).get("timestamp"))
        check_application(envelope, skill_ids)
    except (AlexaVerificationError, ValueError) as exc:
        logger.warning("alexa request rejected: %s", exc)
        return _bad_request()

    reply = await run_in_threadpool(AlexaSkillService(session).handle, envelope)
    return JSONResponse(reply)


@router.post(f"{ALEXA_PATH}/link", response_model=AlexaLinkResultDTO, tags=["alexa"])
@limiter.limit("10/minute")
def link_alexa(
    request: Request,
    body: AlexaLinkRequestDTO,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlexaLinkResultDTO:
    """Link the Alexa account that was read this code to the signed-in person."""
    if not alexa_skill_ids():
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        AlexaLinkService(session).redeem(body.code, current_user.id)
    except AlexaPairingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AlexaLinkResultDTO()
