"""Telegram delivery — sends the audio digest as a voice/audio message.

Uses the Telegram Bot HTTP API directly via aiohttp so we avoid pulling
in the heavy python-telegram-bot SDK as a hard dependency.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiohttp

from screen_time_saver.config import TelegramConfig
from screen_time_saver.models import Digest

log = logging.getLogger(__name__)

_API = "https://api.telegram.org"


def _escape_markdown(text: str) -> str:
    for ch in ("_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        text = text.replace(ch, f"\\{ch}")
    return text


async def deliver_via_telegram(
    digest: Digest,
    audio_path: Path | None,
    config: TelegramConfig,
) -> str:
    """Send the digest to a Telegram chat.

    Sends a text summary first, then the MP3 as an audio message (which
    Telegram renders with an inline player — perfect for podcast-style
    listening).

    Returns a human-readable status string.
    """
    base = f"{_API}/bot{config.bot_token}"

    async with aiohttp.ClientSession() as session:
        # 1. Send a text summary.
        caption_lines = [f"*{_escape_markdown(digest.title)}*", ""]
        for section in digest.sections[:8]:
            caption_lines.append(f"- {_escape_markdown(section.headline)}")
        caption_lines.append(f"\n_{digest.estimated_read_minutes:.0f} min listen_")
        caption_text = "\n".join(caption_lines)

        text_resp = await session.post(
            f"{base}/sendMessage",
            json={
                "chat_id": config.chat_id,
                "text": caption_text,
                "parse_mode": "MarkdownV2",
            },
        )
        text_result = await text_resp.json()
        if not text_result.get("ok"):
            log.error("Telegram sendMessage failed: %s", text_result)
            return f"Telegram: FAILED to send text summary -> chat {config.chat_id}"

        # 2. Send the audio file (if available).
        if audio_path and audio_path.exists():
            data = aiohttp.FormData()
            data.add_field("chat_id", str(config.chat_id))
            data.add_field("title", digest.title)
            data.add_field("performer", "Screen Time Saver")
            data.add_field(
                "audio",
                audio_path.open("rb"),
                filename=audio_path.name,
                content_type="audio/mpeg",
            )

            resp = await session.post(f"{base}/sendAudio", data=data)
            result = await resp.json()

            if not result.get("ok"):
                log.error("Telegram sendAudio failed: %s", result)
                return f"Telegram: text sent, audio FAILED -> chat {config.chat_id}"

            log.info("Audio sent to Telegram chat %s", config.chat_id)
            return f"Telegram: digest + audio sent to chat {config.chat_id}"

        return f"Telegram: text summary sent to chat {config.chat_id} (no audio)"
