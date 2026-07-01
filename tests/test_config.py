"""Configuration parsing tests."""

import pytest

from app.core.config import Settings


@pytest.mark.req("F-1")
def test_cors_origins_parsed_from_csv() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com ,,")
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


@pytest.mark.req("F-1")
def test_cors_origins_accepts_list() -> None:
    settings = Settings(cors_origins=["http://a.com"])
    assert settings.cors_origins == ["http://a.com"]


@pytest.mark.req("F-1")
def test_api_prefix_default() -> None:
    assert Settings().api_v1_prefix == "/api/v1"
