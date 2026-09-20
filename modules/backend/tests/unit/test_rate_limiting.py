"""Rate limiting and how the client address behind it is determined."""
from unittest.mock import MagicMock

import pytest

from modules.backend.src.config import settings
from modules.backend.src.deps import RateLimiter, client_ip


def _request(host="1.2.3.4", forwarded=None):
    request = MagicMock()
    request.headers = {"x-forwarded-for": forwarded} if forwarded else {}
    request.client.host = host
    return request


def test_client_ip_uses_the_socket_address_by_default():
    assert client_ip(_request(host="1.2.3.4")) == "1.2.3.4"


def test_forwarded_header_is_ignored_unless_a_proxy_is_configured(monkeypatch):
    """Otherwise a client forges a new address per request and evades every limit."""
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    assert client_ip(_request(host="1.2.3.4", forwarded="9.9.9.9")) == "1.2.3.4"


def test_forwarded_header_is_used_when_a_proxy_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert client_ip(_request(host="1.2.3.4", forwarded="9.9.9.9")) == "9.9.9.9"


def test_forwarded_chain_takes_the_original_client(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert client_ip(_request(forwarded="9.9.9.9, 10.0.0.1, 10.0.0.2")) == "9.9.9.9"


def test_client_ip_handles_a_missing_client():
    request = MagicMock()
    request.headers = {}
    request.client = None
    assert client_ip(request) == "unknown"


def test_limiter_allows_calls_up_to_the_cap(db):
    limiter = RateLimiter(max_calls=3, window_sec=60, scope="test")
    for _ in range(3):
        limiter.check(db, "client-a")  # must not raise


def test_limiter_blocks_past_the_cap(db):
    from fastapi import HTTPException

    limiter = RateLimiter(max_calls=3, window_sec=60, scope="test")
    for _ in range(3):
        limiter.check(db, "client-a")

    with pytest.raises(HTTPException) as excinfo:
        limiter.check(db, "client-a")
    assert excinfo.value.status_code == 429
    assert "Retry-After" in excinfo.value.headers


def test_limiter_counts_each_client_separately(db):
    limiter = RateLimiter(max_calls=2, window_sec=60, scope="test")
    limiter.check(db, "client-a")
    limiter.check(db, "client-a")
    limiter.check(db, "client-b")  # a different client is unaffected


def test_limiter_scopes_are_independent(db):
    login = RateLimiter(max_calls=1, window_sec=60, scope="login")
    signup = RateLimiter(max_calls=1, window_sec=60, scope="signup")
    login.check(db, "client-a")
    signup.check(db, "client-a")  # exhausting one scope must not close the other
