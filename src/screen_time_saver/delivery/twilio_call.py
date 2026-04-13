"""Twilio outbound call delivery.

Places a phone call to the configured number and plays the audio digest
using Twilio's <Play> TwiML verb. The MP3 must be accessible via a
public URL.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from screen_time_saver.config import TwilioConfig
from screen_time_saver.models import Digest

log = logging.getLogger(__name__)


async def deliver_via_twilio(
    digest: Digest,
    audio_path: Path | None,
    config: TwilioConfig,
) -> str:
    """Place an outbound call that plays the audio digest.

    Returns a human-readable status string.
    """
    if audio_path is None or not audio_path.exists():
        return "Twilio: skipped (no audio file)"

    if not config.audio_base_url:
        raise ValueError(
            "Twilio delivery requires 'audio_base_url' to be a public URL that "
            "Twilio can reach. Localhost is not valid for Twilio playback."
        )

    # Lazy import — twilio is an optional dependency.
    from twilio.rest import Client  # type: ignore[import-untyped]

    client = Client(config.account_sid, config.auth_token)
    mp3_url = f"{config.audio_base_url.rstrip('/')}/{audio_path.name}"

    # TwiML that plays the audio.
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'  <Say voice="Polly.Matthew">Hello! Here is your Screen Time Saver digest: {digest.title}.</Say>'
        f'  <Play>{mp3_url}</Play>'
        '  <Say voice="Polly.Matthew">That\'s your digest for today. Goodbye!</Say>'
        "</Response>"
    )

    # Place the call (runs sync Twilio SDK in a thread).
    loop = asyncio.get_event_loop()
    call = await loop.run_in_executor(
        None,
        lambda: client.calls.create(
            twiml=twiml,
            to=config.to_phone,
            from_=config.from_phone,
        ),
    )

    log.info("Twilio call SID: %s -> %s", call.sid, config.to_phone)
    return f"Twilio: call placed to {config.to_phone} (SID {call.sid})"
