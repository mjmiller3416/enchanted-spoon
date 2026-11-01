"""app/core/rate_limit.py

Shared slowapi Limiter instance for throttling abuse-prone endpoints.

Buckets are per caller, not per IP: behind Railway's proxy every request can
arrive from the same proxy address, which would put all users in one shared
bucket (one user's feedback spam would lock everyone out). The key is the
signed-in user (JWT ``sub``), else the integration API key, else the IP.
"""

import hashlib

from typing import Callable, Iterable

from jose import jwt
from limits import parse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.wrappers import Limit
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

    return f"ip:{client_ip(request)}"


limiter = Limiter(key_func=rate_limit_key)


def client_ip(request: Request) -> str:
    """Client address for the per-IP limiter.

    Railway's edge proxy appends the connecting client to ``X-Forwarded-For``.
    The leftmost entry is whatever the caller sent and is spoofable, so it is
    not used. The rightmost entry is the hop Railway appended. When the header
    is absent, the socket peer (``request.client.host``) is used.

    uvicorn ``--proxy-headers`` is not enabled. ``--forwarded-allow-ips='*'``
    would trust the whole chain and typically surface the spoofable leftmost
    address. An allowlist of Railway proxy IPs is not fixed in this repo.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [part.strip() for part in forwarded.split(",") if part.strip()]
    if parts:
        return parts[-1]
    return get_remote_address(request)


ip_limiter = Limiter(key_func=client_ip)

# Per-route budgets. Checked before monthly/trial quota is reserved.
ASSISTANT_USER_LIMITS = ("10/minute", "60/hour")
ASSISTANT_IP_LIMITS = ("30/minute",)
IMAGE_USER_LIMITS = ("3/minute", "15/hour")
IMAGE_IP_LIMITS = ("6/minute",)
GENERATION_USER_LIMITS = ("5/minute",)
GENERATION_IP_LIMITS = ("15/minute",)
LIGHT_USER_LIMITS = ("10/minute",)
LIGHT_IP_LIMITS = ("30/minute",)


def enforce_pre_quota_limits(
    request: Request,
    user_limits: Iterable[str] = (),
    ip_limits: Iterable[str] = (),
) -> None:
    """Consume per-minute/hour buckets before a route reserves monthly quota.

    Sets ``_rate_limiting_complete`` so a stacked slowapi decorator does not
    count the same request twice. A 429 raised here happens before reserve().
    """
    scope = request.url.path
    _consume(limiter, request, user_limits, rate_limit_key, scope)
    _consume(ip_limiter, request, ip_limits, client_ip, f"{scope}:ip")
    request.state.view_rate_limit = None
    request.state._rate_limiting_complete = True


def _consume(
    bucket: Limiter,
    request: Request,
    specs: Iterable[str],
    key_func: Callable[..., str],
    scope: str,
) -> None:
    for spec in specs:
        item = parse(spec)
        wrapped = Limit(
            limit=item,
            key_func=key_func,
            scope=scope,
            per_method=False,
            methods=None,
            error_message=None,
            exempt_when=None,
            cost=1,
            override_defaults=True,
        )
        key = key_func(request)
        if not bucket.limiter.hit(item, key, scope):
            raise RateLimitExceeded(wrapped)
