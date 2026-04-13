"""Twilio outbound call delivery.

Places a phone call to the configured number and plays the audio digest
using Twilio's <Play> TwiML verb.  The MP3 must be accessible via a
public URL — this module handles that by either:

  1. Using a user-provided ``audio_base_url`` (e.g. an S3 bucket, ngrok tunnel,
     or any static file host), or
  2. Starting a lightweight temporary HTTP server on the configured port
     (useful for local development with an ngrok tunnel).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from screen_time_saver.config import TwilioConfig
from screen_time_saver.models import Digest

log = logging.getLogger(__name__)


def _start_file_server(directory: Path, port: int) -> HTTPServer:
    """Start a background HTTP server serving *directory* on *port*."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Temporary file server on port %d serving %s", port, directory)
    return server


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

    # Lazy import — twilio is an optional dependency.
    from twilio.rest import Client  # type: ignore[import-untyped]

    client = Client(config.account_sid, config.auth_token)

    # Build the public URL for the MP3.
    if config.audio_base_url:
        mp3_url = f"{config.audio_base_url.rstrip('/')}/{audio_path.name}"
    else:
        # Fall back to a local file server (needs ngrok or similar for Twilio).
        port = config.local_server_port
        _start_file_server(audio_path.parent, port)
        mp3_url = f"http://localhost:{port}/{audio_path.name}"
        log.warning(
            "Using local file server at %s — Twilio cannot reach localhost. "
            "Set 'audio_base_url' or use an ngrok tunnel.",
            mp3_url,
        )

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

    log.info("Twilio call SID: %s → %s", call.sid, config.to_phone)
    return f"Twilio: call placed to {config.to_phone} (SID {call.sid})"
