"""Errands integration tests: publish, browse, accept, complete + settle, cancel."""

import pytest
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.payments.models import LedgerEntry, Payment, PaymentRefType, PaymentStatus
from app.users.models import Role, User
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _grant_collaborator(phone: str) -> None:
    user = await User.find_one(User.phone == phone)
    assert user is not None
    user.roles.append(Role.COLLABORATOR)
    await user.save()


def _errand_payload(fee: int = 8000) -> dict[str, object]:
    return {
        "title": "Comprar arroz y aceite",
        "dropoff": {
            "label": "Casa",
            "line": "Cra 9",
            "geo": {"type": "Point", "coordinates": BOGOTA},
        },
        "offered_fee": fee,
        "estimated_cost": 20000,
    }


@pytest.mark.req("E-1", "E-2", "E-3")
async def test_publish_browse_accept_complete_and_settle(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    client_h = _auth(await register_user("+573050000001"))
    created = await api.post("/api/v1/errands", json=_errand_payload(8000), headers=client_h)
    assert created.status_code == 201, created.text
    errand = created.json()
    assert errand["status"] == "open"
    errand_id = errand["id"]

    # collaborator browses nearby open errands
    collab_h = _auth(await register_user("+573050000002"))
    await _grant_collaborator("+573050000002")
    available = await api.get(
        f"/api/v1/errands/available?near={BOGOTA[0]},{BOGOTA[1]}&radius=4000", headers=collab_h
    )
    assert errand_id in [e["id"] for e in available.json()]

    # accept → in_progress → completed
    assert (await api.post(f"/api/v1/errands/{errand_id}/accept", headers=collab_h)).json()[
        "status"
    ] == "assigned"

    # the collaborator can now list it under their assigned errands
    assigned = await api.get("/api/v1/errands/assigned", headers=collab_h)
    assert errand_id in [e["id"] for e in assigned.json()]
    assert (
        await api.post(
            f"/api/v1/errands/{errand_id}/status", json={"status": "in_progress"}, headers=collab_h
        )
    ).json()["status"] == "in_progress"
    completed = await api.post(
        f"/api/v1/errands/{errand_id}/status", json={"status": "completed"}, headers=collab_h
    )
    assert completed.json()["status"] == "completed"

    # cash payment settled: collaborator earns the offered fee
    oid = PydanticObjectId(errand_id)
    payment = await Payment.find_one(
        Payment.ref_type == PaymentRefType.ERRAND, Payment.ref_id == oid
    )
    assert payment is not None and payment.status == PaymentStatus.APPROVED
    assert payment.amount == 8000
    entries = await LedgerEntry.find(
        LedgerEntry.ref_type == PaymentRefType.ERRAND, LedgerEntry.ref_id == oid
    ).to_list()
    assert len(entries) == 1 and entries[0].amount == 8000


@pytest.mark.req("E-1")
async def test_cancel_open_errand(api: AsyncClient, register_user: RegisterUser) -> None:
    client_h = _auth(await register_user("+573050000003"))
    errand_id = (
        await api.post("/api/v1/errands", json=_errand_payload(), headers=client_h)
    ).json()["id"]

    cancelled = await api.post(
        f"/api/v1/errands/{errand_id}/cancel", json={"reason": "ya no"}, headers=client_h
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


@pytest.mark.req("E-1")
async def test_stranger_cannot_read_errand(api: AsyncClient, register_user: RegisterUser) -> None:
    client_h = _auth(await register_user("+573050000004"))
    errand_id = (
        await api.post("/api/v1/errands", json=_errand_payload(), headers=client_h)
    ).json()["id"]

    stranger_h = _auth(await register_user("+573050000005"))
    resp = await api.get(f"/api/v1/errands/{errand_id}", headers=stranger_h)
    assert resp.status_code == 403
