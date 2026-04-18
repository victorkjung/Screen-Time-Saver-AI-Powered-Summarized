"""Twilio outbound call delivery — VGH standard call block.

Copies the audio to the public voice-audio directory, re-encodes for
Twilio compatibility (MPEG-1 44.1kHz mono), verifies the URL is
reachable, then places the call with a simple <Play> TwiML.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from screen_time_saver.config import TwilioConfig
from screen_time_saver.models import Digest

log = logging.getLogger(__name__)

VOICE_AUDIO_DIR = Path('/var/www/voice-audio')
AUDIO_BASE_URL = 'https://voice.vgh-usa.com/audio'


async def deliver_via_twilio(
    digest: Digest,
    audio_path: Path | None,
    config: TwilioConfig,
) -> str:
    """Place an outbound call that plays the audio digest."""
    if audio_path is None or not audio_path.exists():
        return 'Twilio: skipped (no audio file)'

    from twilio.rest import Client

    # 1. Copy and re-encode to MPEG-1 44.1kHz mono (Twilio-safe).
    ts = datetime.now().strftime('%Y-%m-%d-%H%M')
    fname = f'sts-digest-{ts}.mp3'
    final_path = VOICE_AUDIO_DIR / fname
    tmp_path = VOICE_AUDIO_DIR / f'{fname}.tmp.mp3'

    VOICE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(audio_path, tmp_path)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: subprocess.run(
        ['ffmpeg', '-y', '-i', str(tmp_path),
         '-ar', '44100', '-ac', '1', '-codec:a', 'libmp3lame',
         str(final_path)],
        capture_output=True, check=True,
    ))
    tmp_path.unlink(missing_ok=True)

    audio_url = f'{AUDIO_BASE_URL}/{fname}'
    log.info('Audio published at: %s', audio_url)

    # 2. Verify URL is reachable.
    verify = await loop.run_in_executor(None, lambda: subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', audio_url],
        capture_output=True, text=True,
    ))
    status_code = verify.stdout.strip()
    log.info('Audio URL check: %s [%s]', audio_url, status_code)
    if status_code != '200':
        return f'Twilio: FAILED — audio URL returned {status_code}'

    # 3. Place call with simple <Play> TwiML (proven VGH pattern).
    twiml = f'<Response><Play>{audio_url}</Play></Response>'

    call = await loop.run_in_executor(
        None,
        lambda: Client(config.account_sid, config.auth_token).calls.create(
            twiml=twiml,
            to=config.to_phone,
            from_=config.from_phone,
        ),
    )

    log.info('Twilio call SID: %s -> %s', call.sid, config.to_phone)
    return f'Twilio: call placed to {config.to_phone} (SID {call.sid})'
