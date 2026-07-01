"""Admin-owned platform configuration (singleton). See docs/ADMIN_PANEL.md §2.6."""

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PlatformConfig(Document):
    default_commission_rate: float = 0.10
    settlement_frequency_days: int = 15
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "platform_config"
