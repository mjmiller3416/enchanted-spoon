"""Rate-limit buckets are per caller, not per (shared proxy) IP."""

from jose import jwt
from starlette.requests import Request

from app.core.rate_limit import rate_limit_key


def _request(headers: dict, client=("10.0.0.1", 1234)) -> Request:
    return Request(
        {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": client,
        }
    )


def test_signed_in_users_get_their_own_buckets_behind_one_proxy():
    a = jwt.encode({"sub": "user_a"}, "k", algorithm="HS256")
    b = jwt.encode({"sub": "user_b"}, "k", algorithm="HS256")
    assert rate_limit_key(_request({"Authorization": f"Bearer {a}"})) == "user:user_a"
    assert rate_limit_key(_request({"Authorization": f"Bearer {b}"})) == "user:user_b"


def test_integration_key_and_ip_fallbacks():
    key_bucket = rate_limit_key(_request({"X-API-Key": "secret"}))
    assert key_bucket.startswith("key:") and "secret" not in key_bucket
    assert rate_limit_key(_request({})) == "ip:10.0.0.1"


def test_garbage_token_still_gets_a_bucket():
    assert rate_limit_key(_request({"Authorization": "Bearer not-a-jwt"})).startswith("token:")
