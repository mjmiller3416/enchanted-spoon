"""app/services/alexa/verification.py

Proves a request to ``/api/alexa`` came from Alexa, as Amazon requires of a
skill hosted on its own web service:

1. ``SignatureCertChainUrl`` is ``https://s3.amazonaws.com/echo.api/...``
   (port 443 if given, path normalized before the check).
2. The PEM chain at that URL is valid right now, chains to a trusted root
   (certifi's bundle) and its leaf is issued for ``echo-api.amazon.com``.
3. ``Signature-256`` is the base64 RSA-SHA256 (PKCS#1 v1.5) signature of the
   raw request body by that leaf's key.
4. The request's ``timestamp`` is within 150 seconds of now.
5. The request names our skill (``ALEXA_SKILL_ID``).

A verified chain's key is cached per URL until the leaf expires, so only the
first request (per process, per Amazon cert rotation) downloads anything.
"""

from __future__ import annotations

import base64
import binascii
import logging
import posixpath
import re
import threading
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, FrozenSet, List, Optional
from urllib.parse import urlsplit

import certifi
import httpx
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.verification import PolicyBuilder, Store, VerificationError

logger = logging.getLogger(__name__)

CERT_HOST = "s3.amazonaws.com"
CERT_PATH_PREFIX = "/echo.api/"
SIGNING_NAME = "echo-api.amazon.com"
MAX_CLOCK_SKEW = timedelta(seconds=150)
MAX_CHAIN_BYTES = 64 * 1024
_PEM_BLOCK = re.compile(rb"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", re.DOTALL)


class AlexaVerificationError(Exception):
    """The request can't be shown to come from Alexa for this skill. The message is for logs only."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Individual checks ───────────────────────────────────────────────────────
def validate_cert_url(url: Optional[str]) -> None:
    """Amazon's rules for ``SignatureCertChainUrl``.

    Raises:
        AlexaVerificationError: Any rule broken.
    """
    if not url:
        raise AlexaVerificationError("Missing SignatureCertChainUrl.")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise AlexaVerificationError("Malformed SignatureCertChainUrl.")
    if parts.scheme.lower() != "https":
        raise AlexaVerificationError("Cert URL is not https.")
    if (parts.hostname or "").lower() != CERT_HOST:
        raise AlexaVerificationError("Cert URL host is not s3.amazonaws.com.")
    if port not in (None, 443):
        raise AlexaVerificationError("Cert URL port is not 443.")
    if not posixpath.normpath(parts.path).startswith(CERT_PATH_PREFIX):
        raise AlexaVerificationError("Cert URL path is not under /echo.api/.")


def check_timestamp(value: Any, now: Optional[datetime] = None) -> None:
    """The request's ISO 8601 ``timestamp`` must be within 150 seconds of now.

    Raises:
        AlexaVerificationError: Missing, malformed or too old/new.
    """
    if not isinstance(value, str) or not value:
        raise AlexaVerificationError("Missing request timestamp.")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AlexaVerificationError("Malformed request timestamp.")
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    if abs((now or _now()) - stamp) > MAX_CLOCK_SKEW:
        raise AlexaVerificationError("Request timestamp is outside the allowed window.")


def application_id(envelope: Dict[str, Any]) -> Optional[str]:
    """The skill ID a request names (context first, then the session)."""
    context_app = (((envelope.get("context") or {}).get("System") or {}).get("application") or {})
    session_app = ((envelope.get("session") or {}).get("application") or {})
    value = context_app.get("applicationId") or session_app.get("applicationId")
    return value if isinstance(value, str) else None


def check_application(envelope: Dict[str, Any], skill_ids: FrozenSet[str]) -> None:
    """The request must be for one of our skills.

    Raises:
        AlexaVerificationError: Another skill's request (or none named).
    """
    if application_id(envelope) not in skill_ids:
        raise AlexaVerificationError("Request is for another skill.")


# ── Certificate chain + signature ───────────────────────────────────────────
def _download(url: str) -> bytes:
    """Fetch a cert chain (no redirects, small, quick)."""
    with httpx.Client(timeout=5.0, follow_redirects=False) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise AlexaVerificationError(f"Cert chain download answered {response.status_code}.")
    if len(response.content) > MAX_CHAIN_BYTES:
        raise AlexaVerificationError("Cert chain is too large.")
    return response.content


def _load_pem_blocks(data: bytes) -> List[x509.Certificate]:
    """Every certificate in a PEM bundle, skipping any this cryptography release won't parse."""
    certs: List[x509.Certificate] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a few roots in certifi carry non-positive serials
        for block in _PEM_BLOCK.findall(data):
            try:
                certs.append(x509.load_pem_x509_certificate(block))
            except ValueError:
                continue
    return certs


_roots: Optional[Store] = None
_roots_lock = threading.Lock()


def default_roots() -> Store:
    """certifi's trusted roots (loaded once)."""
    global _roots
    with _roots_lock:
        if _roots is None:
            with open(certifi.where(), "rb") as handle:
                _roots = Store(_load_pem_blocks(handle.read()))
        return _roots


@dataclass(frozen=True)
class _VerifiedKey:
    key: rsa.RSAPublicKey
    not_before: datetime
    not_after: datetime


class SignatureVerifier:
    """Checks ``SignatureCertChainUrl`` + ``Signature-256`` against a raw body.

    ``fetch``, ``roots`` and ``clock`` are replaceable for tests.
    """

    def __init__(
        self,
        fetch: Callable[[str], bytes] = _download,
        roots: Optional[Callable[[], Store]] = None,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._fetch = fetch
        self._roots = roots or default_roots
        self._clock = clock
        self._cache: Dict[str, _VerifiedKey] = {}
        self._lock = threading.Lock()

    def _key_for(self, cert_url: str) -> rsa.RSAPublicKey:
        now = self._clock()
        with self._lock:
            cached = self._cache.get(cert_url)
        if cached and cached.not_before <= now < cached.not_after:
            return cached.key

        certs = _load_pem_blocks(self._fetch(cert_url))
        if not certs:
            raise AlexaVerificationError("Cert chain holds no certificates.")
        leaf, intermediates = certs[0], certs[1:]
        try:
            verifier = (
                PolicyBuilder()
                .store(self._roots())
                .time(now)
                .build_server_verifier(x509.DNSName(SIGNING_NAME))
            )
            verifier.verify(leaf, intermediates)
        except VerificationError as exc:
            raise AlexaVerificationError(f"Cert chain failed validation: {exc}")
        key = leaf.public_key()
        if not isinstance(key, rsa.RSAPublicKey):
            raise AlexaVerificationError("Signing cert key is not RSA.")
        with self._lock:
            self._cache[cert_url] = _VerifiedKey(key, leaf.not_valid_before_utc, leaf.not_valid_after_utc)
        return key

    def verify(self, cert_url: Optional[str], signature: Optional[str], body: bytes) -> None:
        """Raise unless ``signature`` is the chain's signature of ``body``.

        Raises:
            AlexaVerificationError: Bad URL, chain, encoding or signature.
        """
        validate_cert_url(cert_url)
        if not signature:
            raise AlexaVerificationError("Missing Signature-256 header.")
        try:
            raw = base64.b64decode(signature, validate=True)
        except (binascii.Error, ValueError):
            raise AlexaVerificationError("Signature is not base64.")
        key = self._key_for(cert_url)  # type: ignore[arg-type]  (validated above)
        try:
            key.verify(raw, body, padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature:
            raise AlexaVerificationError("Signature does not match the body.")


_default_verifier: Optional[SignatureVerifier] = None


def default_verifier() -> SignatureVerifier:
    """The process-wide verifier (one cert cache)."""
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = SignatureVerifier()
    return _default_verifier
