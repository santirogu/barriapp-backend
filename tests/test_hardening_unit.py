"""Unit tests for rate-limit config mapping (no DB)."""

import pytest

from app.core.config import Settings
from app.core.middleware import build_security_headers
from app.core.ratelimit import _limits


@pytest.mark.req("A-5")
def test_rate_limit_mapping() -> None:
    s = Settings()
    assert _limits(s)["login"] == (s.login_rate_limit, s.login_rate_window)
    assert _limits(s)["ai_chat"] == (s.ai_chat_rate_limit, s.ai_chat_rate_window)


@pytest.mark.req("A-5")
def test_security_headers_hsts_toggle() -> None:
    without = dict(build_security_headers(enable_hsts=False, hsts_max_age=100))
    assert without[b"x-content-type-options"] == b"nosniff"
    assert b"strict-transport-security" not in without

    with_hsts = dict(build_security_headers(enable_hsts=True, hsts_max_age=100))
    assert with_hsts[b"strict-transport-security"] == b"max-age=100; includeSubDomains"
