"""app/core/rate_limit.py

Shared slowapi Limiter instance for throttling abuse-prone endpoints.

Buckets are per caller, not per IP: behind Railway's proxy every request can
arrive from the same proxy address, which would put all users in one shared
bucket (one user's feedback spam would lock everyone out). The key is the
signed-in user (JWT ``sub``), else the integration API key, else the IP.
"""

import hashlib

from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def rate_limit_key(request: Request) -> str:
    """
    Identify the caller for rate limiting.

    The JWT is read *unverified* here: this only picks a bucket, and the route's
    auth dependency still rejects a forged token. A forged ``sub`` would only
    move the forger into a different bucket of their own.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            sub = jwt.get_unverified_claims(token).get("sub")
        except Exception:
            sub = None
        return f"user:{sub}" if sub else f"token:{_digest(token)}"

    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{_digest(api_key)}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key)
