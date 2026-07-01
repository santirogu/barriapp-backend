"""Payments endpoints. See docs/API_CONTRACT.md §10 and
docs/COMMISSION_AND_SUBSCRIPTION.md."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Header

from app.core.deps import CurrentUser
from app.payments import service
from app.payments.schemas import (
    IntentRequest,
    IntentResponse,
    PaymentPublic,
    WebhookAck,
    WompiWebhookIn,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/intent", response_model=IntentResponse)
async def create_intent(data: IntentRequest, user: CurrentUser) -> IntentResponse:
    return await service.create_intent(user, PydanticObjectId(data.order_id))


@router.post("/webhook/wompi", response_model=WebhookAck)
async def wompi_webhook(
    payload: WompiWebhookIn,
    x_event_signature: Annotated[str | None, Header()] = None,
) -> WebhookAck:
    await service.handle_wompi_webhook(payload, x_event_signature)
    return WebhookAck()


@router.get("/{payment_id}", response_model=PaymentPublic)
async def get_payment(payment_id: PydanticObjectId, user: CurrentUser) -> PaymentPublic:
    return PaymentPublic.from_payment(await service.get_payment(user, payment_id))
