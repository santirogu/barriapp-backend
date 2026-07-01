"""Unit tests for settlement logic (no DB)."""

import pytest

from app.settlements.logic import summarize_commissions


@pytest.mark.req("P-7")
def test_summarize_commissions() -> None:
    total, orders = summarize_commissions([(1000, "o1"), (500, "o2"), (300, "o1")])
    assert total == 1800
    assert orders == 2  # distinct order refs


@pytest.mark.req("P-7")
def test_summarize_commissions_empty() -> None:
    assert summarize_commissions([]) == (0, 0)
