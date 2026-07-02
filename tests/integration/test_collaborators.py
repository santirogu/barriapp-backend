"""Collaborator onboarding integration tests (U-5, D-2, D-6)."""

import pytest
from httpx import AsyncClient

from app.users.models import Role, User
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _promote_to_admin(phone: str) -> None:
    user = await User.find_one(User.phone == phone)
    assert user is not None
    user.roles.append(Role.SUPER_ADMIN)
    await user.save()


_BECOME = {"vehicle_type": "bike", "id_number": "1032456789"}


@pytest.mark.req("U-5", "D-6", "D-2")
async def test_onboarding_verification_and_go_online(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    collab_h = _auth(await register_user("+573020000001"))

    created = await api.post("/api/v1/me/become-collaborator", json=_BECOME, headers=collab_h)
    assert created.status_code == 201, created.text
    profile = created.json()
    assert profile["verification_status"] == "pending"
    collab_user_id = profile["user_id"]

    # cannot go online before approval
    early = await api.post(
        "/api/v1/collaborator/availability",
        json={"status": "online", "lng": -74.081, "lat": 4.609},
        headers=collab_h,
    )
    assert early.status_code == 403
    assert early.json()["error"]["code"] == "not_approved"

    # admin approves (promote a user to super_admin directly for the test)
    admin_h = _auth(await register_user("+573020000002"))
    await _promote_to_admin("+573020000002")

    # admin sees the pending collaborator in the verification queue
    queue = await api.get("/api/v1/admin/collaborators?status=pending", headers=admin_h)
    assert queue.status_code == 200, queue.text
    assert collab_user_id in [c["user_id"] for c in queue.json()]

    approved = await api.patch(
        f"/api/v1/collaborator/{collab_user_id}/verification",
        json={"status": "approved"},
        headers=admin_h,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["verification_status"] == "approved"

    # now the collaborator can go online
    online = await api.post(
        "/api/v1/collaborator/availability",
        json={"status": "online", "lng": -74.081, "lat": 4.609},
        headers=collab_h,
    )
    assert online.status_code == 200
    assert online.json()["availability"] == "online"

    # role granted on approval
    me = await api.get("/api/v1/me", headers=collab_h)
    assert "collaborator" in me.json()["roles"]


@pytest.mark.req("D-6")
async def test_verification_requires_admin(api: AsyncClient, register_user: RegisterUser) -> None:
    collab_h = _auth(await register_user("+573020000003"))
    profile = (
        await api.post("/api/v1/me/become-collaborator", json=_BECOME, headers=collab_h)
    ).json()

    # a non-admin cannot verify
    resp = await api.patch(
        f"/api/v1/collaborator/{profile['user_id']}/verification",
        json={"status": "approved"},
        headers=collab_h,
    )
    assert resp.status_code == 403
