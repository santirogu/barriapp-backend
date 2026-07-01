"""OTP delivery (SMS).

Dev/test logs the code so the flow works without a real gateway; production will
integrate a real SMS provider (e.g. Twilio or a local Colombian provider).
"""

import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


async def send_otp(phone: str, code: str) -> None:
    settings = get_settings()
    if settings.is_production:
        # TODO: integrate a real SMS provider; never log the code in production.
        logger.info("otp_dispatch", phone=phone)
    else:
        logger.info("otp_dev", phone=phone, code=code)
