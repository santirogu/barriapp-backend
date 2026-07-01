"""Unit tests for pure payment logic (no DB): ledger split + webhook signature."""

import pytest

from app.payments.logic import (
    LedgerType,
    compute_ledger_lines,
    verify_wompi_signature,
    wompi_signature,
)


@pytest.mark.req("P-4")
def test_ledger_split_with_collaborator() -> None:
    lines = compute_ledger_lines(
        items_total=10000,
        delivery_fee=2000,
        platform_fee=1000,
        collaborator_id="c1",
        seller_id="s1",
        settled=True,
    )
    by_type = {line.type: line for line in lines}
    assert by_type[LedgerType.EARNING].user_id in {"c1", "s1"}
    # collaborator earning = delivery fee
    collab = next(x for x in lines if x.user_id == "c1")
    assert collab.amount == 2000
    # seller earning = items - commission
    seller = next(x for x in lines if x.user_id == "s1")
    assert seller.amount == 9000
    # platform commission
    commission = next(x for x in lines if x.type == LedgerType.COMMISSION)
    assert commission.amount == 1000 and commission.user_id is None


@pytest.mark.req("P-4")
def test_ledger_split_without_collaborator_and_unsettled() -> None:
    lines = compute_ledger_lines(
        items_total=5000,
        delivery_fee=0,
        platform_fee=500,
        collaborator_id=None,
        seller_id="s1",
        settled=False,
    )
    assert len(lines) == 2  # no collaborator line
    commission = next(x for x in lines if x.type == LedgerType.COMMISSION)
    assert commission.settled is False  # cash commission is a receivable


@pytest.mark.req("P-3")
def test_wompi_signature_roundtrip() -> None:
    sig = wompi_signature(reference="BA-1", transaction_id="txn_1", status="APPROVED", secret="s")
    assert verify_wompi_signature(
        reference="BA-1", transaction_id="txn_1", status="APPROVED", secret="s", provided=sig
    )
    assert not verify_wompi_signature(
        reference="BA-1", transaction_id="txn_1", status="APPROVED", secret="s", provided="bad"
    )
