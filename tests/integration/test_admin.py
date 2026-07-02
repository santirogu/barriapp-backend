"""Admin integration tests: metrics, user moderation, audit access, config."""

import pytest
from httpx import AsyncClient

from app.users.models import Role, User
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _promote_to_admin(phone: str) -> None:
    user = await User.find_one(User.phone == phone)
    assert user is not None
    user.role = Role.SUPER_ADMIN
    await user.save()


@pytest.mark.req("AD-1", "AD-2", "AD-3")
async def test_admin_metrics_users_audit_and_config(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    # seed some data: a seller with a store
    seller_h = _auth(await register_user("+573080000001", "seller"))
    store = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": "Tienda",
                "location": {"line": "Cra 1", "geo": {"type": "Point", "coordinates": BOGOTA}},
            },
            headers=seller_h,
        )
    ).json()
    seller_id = store["owner_id"]

    client_h = _auth(await register_user("+573080000002"))
    admin_h = _auth(await register_user("+573080000003"))
    await _promote_to_admin("+573080000003")

    # non-admin is rejected
    assert (await api.get("/api/v1/admin/metrics", headers=client_h)).status_code == 403

    # metrics
    metrics = await api.get("/api/v1/admin/metrics", headers=admin_h)
    assert metrics.status_code == 200, metrics.text
    body = metrics.json()
    assert body["users"] >= 3
    assert body["stores"] >= 1

    # user management: list + suspend
    users = await api.get("/api/v1/admin/users?role=seller", headers=admin_h)
    assert seller_id in [u["id"] for u in users.json()]
    suspended = await api.patch(
        f"/api/v1/admin/users/{seller_id}/status", json={"status": "suspended"}, headers=admin_h
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    # audit log explorer
    logs = await api.get("/api/v1/admin/audit-logs?module=stores", headers=admin_h)
    assert logs.status_code == 200
    assert any(item["action"] == "store.created" for item in logs.json())

    # config get + patch
    cfg = await api.get("/api/v1/admin/config", headers=admin_h)
    assert cfg.json()["default_commission_rate"] == 0.10
    updated = await api.patch(
        "/api/v1/admin/config", json={"default_commission_rate": 0.12}, headers=admin_h
    )
    assert updated.json()["default_commission_rate"] == 0.12


@pytest.mark.req("AD-2")
async def test_suspended_user_is_blocked(api: AsyncClient, register_user: RegisterUser) -> None:
    victim_h = _auth(await register_user("+573080000004"))
    admin_h = _auth(await register_user("+573080000005"))
    await _promote_to_admin("+573080000005")

    victim = await User.find_one(User.phone == "+573080000004")
    assert victim is not None
    await api.patch(
        f"/api/v1/admin/users/{victim.id}/status", json={"status": "suspended"}, headers=admin_h
    )

    # a suspended user is blocked on protected calls
    resp = await api.get("/api/v1/me", headers=victim_h)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "account_suspended"
