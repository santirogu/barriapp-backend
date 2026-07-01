"""Unit tests for rate-limit config mapping (no DB)."""

import pytest

from app.core.config import Settings
from app.core.ratelimit import _limits


@pytest.mark.req("A-5")
def test_rate_limit_mapping() -> None:
    s = Settings()
    assert _limits(s)["login"] == (s.login_rate_limit, s.login_rate_window)
    assert _limits(s)["ai_chat"] == (s.ai_chat_rate_limit, s.ai_chat_rate_window)
