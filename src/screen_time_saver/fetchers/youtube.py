"""YouTube fetcher — uses yt-dlp to list channel videos and extract transcripts."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import aiohttp
import yt_dlp

from screen_time_saver.config import SourceConfig
from screen_time_saver.fetchers.base import BaseFetcher
from screen_time_saver.models import ContentItem

log = logging.getLogger(__name__)

# yt-dlp options shared across calls.
_QUIET_OPTS: dict = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,  # fast listing without full download
}
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)


def _list_recent_videos(channel_url: str, max_items: int) -> list[dict]:
    """Return basic metadata dicts for the most recent uploads."""
    opts = {**_QUIET_OPTS, "playlistend": max_items}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"{channel_url}/videos", download=False) or {}
    return list((info.get("entries") or [])[:max_items])


def _get_video_info(url: str) -> dict:
    """Return full metadata (including subtitle URLs) for a single video."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False) or {}


async def _fetch_subtitle_text(sub_url: str) -> str:
    """Download a json3 subtitle file and return plain text."""
    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        async with session.get(sub_url) as resp:
            if resp.status != 200:
                return ""
            data = json.loads(await resp.text())

    # json3 format: {"events": [{"segs": [{"utf8": "..."}]}]}
    parts: list[str] = []
    for event in data.get("events", []):
        for seg in event.get("segs", []):
            parts.append(seg.get("utf8", ""))
    return " ".join(parts).strip()


def _best_sub_url(info: dict) -> str | None:
    """Pick the best English subtitle URL (manual > auto, json3 preferred)."""
    for key in ("subtitles", "automatic_captions"):
        subs = info.get(key, {})
        for lang in ("en", "en-US", "en-GB"):
            formats = subs.get(lang, [])
            for fmt in formats:
                if fmt.get("ext") == "json3":
                    return fmt["url"]
            # Fall back to first available format.
            if formats:
                return formats[0].get("url")
    return None


class YouTubeFetcher(BaseFetcher):
    """Fetch recent videos from a YouTube channel and extract transcripts."""

    async def fetch(self, source: SourceConfig) -> list[ContentItem]:
        loop = asyncio.get_event_loop()

        # Step 1 — list recent videos (CPU-bound yt-dlp call).
        entries = await loop.run_in_executor(
            None, _list_recent_videos, source.channel_url, source.max_items
        )

        items: list[ContentItem] = []
        for entry in entries:
            video_url = entry.get("url") or entry.get("webpage_url", "")
            if not video_url:
                continue

            # Step 2 — get full info for each video.
            try:
                info = await loop.run_in_executor(None, _get_video_info, video_url)
            except Exception:
                log.warning("Failed to fetch info for %s", video_url, exc_info=True)
                continue

            # Step 3 — extract transcript text.
            transcript = ""
            sub_url = _best_sub_url(info)
            if sub_url:
                try:
                    transcript = await _fetch_subtitle_text(sub_url)
                except Exception:
                    log.warning("Failed to fetch subs for %s", video_url, exc_info=True)

            if not transcript:
                transcript = info.get("description", "")

            upload_date = info.get("upload_date")  # "YYYYMMDD"
            published = None
            if upload_date and len(upload_date) == 8:
                published = datetime.strptime(upload_date, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )

            items.append(
                ContentItem(
                    source_name=source.name,
                    platform="youtube",
                    title=info.get("title", entry.get("title", "(untitled)")),
                    url=info.get("webpage_url", video_url),
                    content_text=transcript,
                    published=published,
                    duration_seconds=info.get("duration"),
                )
            )

        return items
