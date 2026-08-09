"""app/core/rate_limit.py

Shared slowapi Limiter instance for throttling abuse-prone endpoints.

Keyed by client IP (`get_remote_address`) rather than user ID, since the
limiter must also cover unauthenticated/key-authenticated callers (e.g. the
integration API) uniformly.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
