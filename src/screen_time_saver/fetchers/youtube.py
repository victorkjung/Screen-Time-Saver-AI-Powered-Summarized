"""YouTube fetcher — yt-dlp for listing, youtube-transcript-api for transcripts."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

from screen_time_saver.config import SourceConfig
from screen_time_saver.fetchers.base import BaseFetcher
from screen_time_saver.models import ContentItem

log = logging.getLogger(__name__)

# yt-dlp options for fast channel listing (no downloads, no subtitles).
_QUIET_OPTS: dict = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
}


def _build_transcript_api() -> YouTubeTranscriptApi:
    """Build a YouTubeTranscriptApi instance, optionally with a SOCKS proxy.

    Set YOUTUBE_PROXY_URL (e.g. ``socks5://100.126.103.83:1080``) to route
    transcript requests through a residential IP.
    """
    proxy_url = os.environ.get("YOUTUBE_PROXY_URL")
    if proxy_url:
        log.info("Using YouTube transcript proxy: %s", proxy_url)
        proxy = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        return YouTubeTranscriptApi(proxy_config=proxy)
    return YouTubeTranscriptApi()


def _extract_video_id(url: str) -> str | None:
    """Extract a YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _list_recent_videos(channel_url: str, max_items: int) -> list[dict]:
    """Return basic metadata dicts for the most recent uploads."""
    opts = {**_QUIET_OPTS, "playlistend": max_items}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"{channel_url}/videos", download=False) or {}
    return list((info.get("entries") or [])[:max_items])


def _get_video_info(url: str) -> dict | None:
    """Return metadata for a single video. Returns None on failure."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False) or {}
    except Exception:
        return None


def _fetch_transcript(ytt: YouTubeTranscriptApi, video_id: str) -> str:
    """Fetch transcript text via youtube-transcript-api. Returns empty on failure."""
    try:
        transcript = ytt.fetch(video_id)
        return " ".join(snippet.text for snippet in transcript)
    except Exception:
        log.warning("Transcript unavailable for %s", video_id, exc_info=True)
        return ""


class YouTubeFetcher(BaseFetcher):
    """Fetch recent videos from a YouTube channel and extract transcripts."""

    async def fetch(self, source: SourceConfig) -> list[ContentItem]:
        loop = asyncio.get_event_loop()
        ytt = _build_transcript_api()

        # Step 1 — list recent videos (yt-dlp flat listing, works from any IP).
        entries = await loop.run_in_executor(
            None, _list_recent_videos, source.channel_url, source.max_items
        )

        items: list[ContentItem] = []
        for entry in entries:
            video_url = entry.get("url") or entry.get("webpage_url", "")
            if not video_url:
                continue

            video_id = _extract_video_id(video_url)

            # Step 2 — try full metadata via yt-dlp (may fail on datacenter IPs).
            info = await loop.run_in_executor(None, _get_video_info, video_url)
            if info is None:
                log.info("yt-dlp metadata blocked for %s, using listing data", video_url)

            # Step 3 — transcript via youtube-transcript-api (proxied).
            transcript = ""
            if video_id:
                transcript = await loop.run_in_executor(
                    None, _fetch_transcript, ytt, video_id
                )

            # Fall back to description from whichever source has it.
            if not transcript:
                transcript = (info or {}).get("description", "") or entry.get("description", "")

            # Build published date from info or entry.
            upload_date = (info or {}).get("upload_date") or entry.get("upload_date")
            published = None
            if upload_date and len(str(upload_date)) == 8:
                published = datetime.strptime(str(upload_date), "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )

            # Prefer info metadata, fall back to flat listing fields.
            title = (info or {}).get("title") or entry.get("title", "(untitled)")
            url = (info or {}).get("webpage_url") or video_url
            duration = (info or {}).get("duration") or entry.get("duration")

            items.append(
                ContentItem(
                    source_name=source.name,
                    platform="youtube",
                    title=title,
                    url=url,
                    content_text=transcript,
                    published=published,
                    duration_seconds=duration,
                )
            )

        return items
