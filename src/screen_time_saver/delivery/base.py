"""Delivery dispatcher — routes to the configured backend(s)."""

from __future__ import annotations

import logging
from pathlib import Path

from screen_time_saver.config import DeliveryConfig
from screen_time_saver.models import Digest

log = logging.getLogger(__name__)


async def deliver_digest(
    digest: Digest,
    audio_path: Path | None,
    config: DeliveryConfig,
) -> list[str]:
    """Deliver the digest via every enabled backend.

    Returns a list of human-readable status strings (one per backend).
    """
    results: list[str] = []

    if config.twilio and config.twilio.enabled:
        from screen_time_saver.delivery.twilio_call import deliver_via_twilio

        try:
            msg = await deliver_via_twilio(digest, audio_path, config.twilio)
            results.append(msg)
        except Exception:
            log.error("Twilio delivery failed", exc_info=True)
            results.append("Twilio: FAILED (see logs)")

    if config.telegram and config.telegram.enabled:
        from screen_time_saver.delivery.telegram_bot import deliver_via_telegram

        try:
            msg = await deliver_via_telegram(digest, audio_path, config.telegram)
            results.append(msg)
        except Exception:
            log.error("Telegram delivery failed", exc_info=True)
            results.append("Telegram: FAILED (see logs)")

    return results
