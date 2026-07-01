"""Pure errand logic (no DB): transitions, cancel rules, code, geo query."""

import secrets
from typing import Any

from app.errands.models import ErrandStatus

# Status advances the assigned collaborator drives.
ERRAND_ADVANCE: dict[ErrandStatus, ErrandStatus] = {
    ErrandStatus.ASSIGNED: ErrandStatus.IN_PROGRESS,
    ErrandStatus.IN_PROGRESS: ErrandStatus.COMPLETED,
}

# Client may cancel while open or assigned (before it is in progress).
CANCELLABLE: frozenset[ErrandStatus] = frozenset({ErrandStatus.OPEN, ErrandStatus.ASSIGNED})


def generate_errand_code() -> str:
    return "MD-" + secrets.token_hex(4).upper()


def next_status(current: ErrandStatus) -> ErrandStatus | None:
    return ERRAND_ADVANCE.get(current)


def can_cancel(current: ErrandStatus) -> bool:
    return current in CANCELLABLE


def build_available_query(near: tuple[float, float], radius_meters: int) -> dict[str, Any]:
    """Open errands near a point (nearest-first via 2dsphere on dropoff)."""
    return {
        "status": ErrandStatus.OPEN.value,
        "dropoff.geo": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [near[0], near[1]]},
                "$maxDistance": radius_meters,
            }
        },
    }
