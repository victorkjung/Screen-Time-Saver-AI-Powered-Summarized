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
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)


def _sanitize_error(exc: Exception, endpoint: str) -> str:
    """Build a safe error message that does NOT include the bot token.

    aiohttp's ``ClientResponseError`` embeds the full request URL in its
    string representation — and the URL contains the bot token. We replace
    it with the endpoint name only.
    """
    status = getattr(exc, "status", "?")
    message = getattr(exc, "message", str(exc))
    return f"{endpoint} returned HTTP {status} ({message})"


async def _post_json(
    session: aiohttp.ClientSession,
    url: str,
    endpoint: str,
    payload: dict,
) -> dict:
    """POST JSON; raise a sanitized error on non-2xx so the token never leaks."""
    async with session.post(url, json=payload) as resp:
        body = await resp.json(content_type=None)
        if resp.status >= 400 or not body.get("ok", True):
            raise RuntimeError(
                f"{endpoint} returned HTTP {resp.status}: {body.get('description', body)}"
            )
        return body


async def _post_multipart(
    session: aiohttp.ClientSession,
    url: str,
    endpoint: str,
    data: aiohttp.FormData,
) -> dict:
    async with session.post(url, data=data) as resp:
        body = await resp.json(content_type=None)
        if resp.status >= 400 or not body.get("ok", True):
            raise RuntimeError(
                f"{endpoint} returned HTTP {resp.status}: {body.get('description', body)}"
            )
        return body


async def deliver_via_telegram(
    digest: Digest,
    audio_path: Path | None,
    config: TelegramConfig,
) -> str:
    """Send the digest to a Telegram chat.

    Sends a text summary first, then the MP3 as an audio message (which
    Telegram renders with an inline player — perfect for podcast-style
    listening).

    Returns a human-readable status string. Never includes the bot token
    in errors — failures are sanitized via :func:`_sanitize_error`.
    """
    base = f"{_API}/bot{config.bot_token}"

    # Build plain-text summary. No MarkdownV2 — avoids escape hell for
    # headlines that may contain any of ``_*[]()~`>#+-=|{}.!`` and makes
    # the output forwardable/quotable without backslash noise.
    lines = [digest.title, ""]
    for section in digest.sections[:8]:
        lines.append(f"• {section.headline}")
    lines.append(f"\n{digest.estimated_read_minutes:.0f} min listen")
    summary_text = "\n".join(lines)

    # Telegram sendMessage has a 4096-char limit. Truncate safely if needed.
    if len(summary_text) > 4000:
        summary_text = summary_text[:3990] + "\n…"

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        # 1. Send text summary.
        try:
            await _post_json(
                session,
                f"{base}/sendMessage",
                "sendMessage",
                {"chat_id": config.chat_id, "text": summary_text},
            )
        except Exception as exc:
            safe = _sanitize_error(exc, "sendMessage")
            log.error("Telegram %s", safe)
            return f"Telegram: FAILED text summary ({safe})"

        # 2. Send audio file (if available).
        if audio_path and audio_path.exists():
            try:
                data = aiohttp.FormData()
                data.add_field("chat_id", str(config.chat_id))
                data.add_field("title", digest.title)
                data.add_field("performer", "Screen Time Saver")
                with audio_path.open("rb") as audio_file:
                    data.add_field(
                        "audio",
                        audio_file,
                        filename=audio_path.name,
                        content_type="audio/mpeg",
                    )
                    await _post_multipart(
                        session, f"{base}/sendAudio", "sendAudio", data
                    )
            except Exception as exc:
                safe = _sanitize_error(exc, "sendAudio")
                log.error("Telegram %s", safe)
                return f"Telegram: text sent, audio FAILED ({safe})"

            log.info("Audio sent to Telegram chat %s", config.chat_id)
            return f"Telegram: digest + audio sent to chat {config.chat_id}"

        return f"Telegram: text summary sent to chat {config.chat_id} (no audio)"
