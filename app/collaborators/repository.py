"""Data access for collaborator profiles (incl. geospatial availability search)."""

from typing import Any

from beanie import PydanticObjectId

from app.collaborators.models import Availability, CollaboratorProfile, VerificationStatus


async def get_by_user_id(user_id: PydanticObjectId) -> CollaboratorProfile | None:
    return await CollaboratorProfile.find_one(CollaboratorProfile.user_id == user_id)


async def insert(profile: CollaboratorProfile) -> CollaboratorProfile:
    return await profile.insert()


def build_available_near_query(near: tuple[float, float], radius_meters: int) -> dict[str, Any]:
    """Pure query builder: approved + online collaborators near a point (nearest-first)."""
    return {
        "verification_status": VerificationStatus.APPROVED.value,
        "availability": Availability.ONLINE.value,
        "current_location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [near[0], near[1]]},
                "$maxDistance": radius_meters,
            }
        },
    }


async def find_available_near(
    near: tuple[float, float], radius_meters: int, *, limit: int = 10
) -> list[CollaboratorProfile]:
    query = build_available_near_query(near, radius_meters)
    return await CollaboratorProfile.find(query).limit(limit).to_list()
