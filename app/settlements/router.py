"""Settlement endpoints. Admin generates/marks-paid; sellers view their own.
See docs/API_CONTRACT.md and docs/COMMISSION_AND_SUBSCRIPTION.md §5."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, require_roles
from app.settlements import service
from app.settlements.schemas import GenerateSettlement, MarkPaid, SettlementPublic
from app.users.models import Role, User

router = APIRouter(tags=["settlements"])

AdminUser = Annotated[User, Depends(require_roles(Role.SUPER_ADMIN))]


@router.post(
    "/admin/settlements", response_model=SettlementPublic, status_code=status.HTTP_201_CREATED
)
async def generate_settlement(data: GenerateSettlement, admin: AdminUser) -> SettlementPublic:
    return SettlementPublic.from_settlement(await service.generate_settlement(admin, data))


@router.get("/admin/settlements", response_model=list[SettlementPublic])
async def list_settlements(
    admin: AdminUser, store_id: str | None = Query(None)
) -> list[SettlementPublic]:
    oid = PydanticObjectId(store_id) if store_id else None
    items = await service.list_settlements(oid)
    return [SettlementPublic.from_settlement(s) for s in items]


@router.post("/admin/settlements/{settlement_id}/pay", response_model=SettlementPublic)
async def mark_paid(
    settlement_id: PydanticObjectId, data: MarkPaid, admin: AdminUser
) -> SettlementPublic:
    return SettlementPublic.from_settlement(await service.mark_paid(admin, settlement_id, data))


@router.get("/settlements", response_model=list[SettlementPublic])
async def my_settlements(user: CurrentUser) -> list[SettlementPublic]:
    items = await service.list_for_seller(user)
    return [SettlementPublic.from_settlement(s) for s in items]
