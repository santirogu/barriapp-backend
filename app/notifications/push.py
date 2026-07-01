"""Push delivery (FCM).

Dev/test logs; production will integrate Firebase Cloud Messaging. Best-effort:
callers never depend on delivery success.
"""

from typing import Any

import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


async def send_push(tokens: list[str], title: str, body: str, data: dict[str, Any]) -> None:
    if not tokens:
        return
    settings = get_settings()
    if settings.is_production:
        # TODO: integrate FCM (firebase-admin / HTTP v1) using the device tokens.
        logger.info("push_dispatch", token_count=len(tokens), title=title)
    else:
        logger.info("push_dev", token_count=len(tokens), title=title, body=body, data=data)
