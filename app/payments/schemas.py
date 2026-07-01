"""Payments I/O schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.payments.models import Payment, PaymentMethod, PaymentRefType, PaymentStatus


class IntentRequest(BaseModel):
    order_id: str


class IntentResponse(BaseModel):
    payment_id: str
    reference: str
    amount: int
    currency: str
    public_key: str
    status: PaymentStatus


class WompiWebhookIn(BaseModel):
    reference: str
    transaction_id: str
    status: str  # "APPROVED" | "DECLINED"


class WebhookAck(BaseModel):
    received: bool = True


class PaymentPublic(BaseModel):
    id: str
    ref_type: PaymentRefType
    ref_id: str
    payer_id: str
    amount: int
    method: PaymentMethod
    status: PaymentStatus
    created_at: datetime

    @classmethod
    def from_payment(cls, payment: Payment) -> "PaymentPublic":
        return cls(
            id=str(payment.id),
            ref_type=payment.ref_type,
            ref_id=str(payment.ref_id),
            payer_id=str(payment.payer_id),
            amount=payment.amount,
            method=payment.method,
            status=payment.status,
            created_at=payment.created_at,
        )
