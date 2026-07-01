"""Pure payment logic (no DB): ledger computation and webhook signature.

The Wompi signature here is a straightforward HMAC over a canonical string; the
exact field concatenation must be aligned with Wompi's events spec at real
integration time (kept isolated so only this function changes).
"""

import hashlib
import hmac

from pydantic import BaseModel

from app.payments.models import LedgerType


class LedgerLine(BaseModel):
    """A computed ledger movement (plain data; mapped to LedgerEntry docs later)."""

    type: LedgerType
    user_id: str | None  # None = platform account
    amount: int
    settled: bool


def compute_ledger_lines(
    *,
    items_total: int,
    delivery_fee: int,
    platform_fee: int,
    collaborator_id: str | None,
    seller_id: str,
    settled: bool,
) -> list[LedgerLine]:
    """Split a delivered order into ledger movements.

    - collaborator earns the delivery fee
    - the platform earns the commission
    - the seller earns the items total minus commission
    ``settled`` is False for cash (commission is a receivable from the seller).
    """
    lines: list[LedgerLine] = []
    if collaborator_id is not None and delivery_fee > 0:
        lines.append(
            LedgerLine(
                type=LedgerType.EARNING, user_id=collaborator_id, amount=delivery_fee, settled=True
            )
        )
    lines.append(
        LedgerLine(type=LedgerType.COMMISSION, user_id=None, amount=platform_fee, settled=settled)
    )
    lines.append(
        LedgerLine(
            type=LedgerType.EARNING,
            user_id=seller_id,
            amount=items_total - platform_fee,
            settled=settled,
        )
    )
    return lines


def wompi_signature(*, reference: str, transaction_id: str, status: str, secret: str) -> str:
    """Compute the expected HMAC-SHA256 signature for a webhook event."""
    message = f"{reference}.{transaction_id}.{status}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_wompi_signature(
    *, reference: str, transaction_id: str, status: str, secret: str, provided: str
) -> bool:
    expected = wompi_signature(
        reference=reference, transaction_id=transaction_id, status=status, secret=secret
    )
    return hmac.compare_digest(expected, provided)
