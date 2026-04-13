"""Twitter / X fetcher via Nitter RSS bridge.

Nitter provides RSS feeds for public Twitter profiles without requiring
an API key.  Instances can be unreliable, so the base URL is configurable
and the fetcher fails gracefully.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from time import mktime

import feedparser

from screen_time_saver.config import SourceConfig
from screen_time_saver.fetchers.base import BaseFetcher
from screen_time_saver.models import ContentItem

log = logging.getLogger(__name__)

# Public Nitter instances — tried in order until one responds.
_NITTER_BASES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


class TwitterFetcher(BaseFetcher):
    """Fetch recent tweets for a public profile via Nitter RSS."""

    async def fetch(self, source: SourceConfig) -> list[ContentItem]:
        handle = (source.handle or "").lstrip("@")

        feed = None
        for base in _NITTER_BASES:
            url = f"{base}/{handle}/rss"
            parsed = feedparser.parse(url)
            if parsed.entries:
                feed = parsed
                break
            log.debug("No entries from %s", url)

        if feed is None or not feed.entries:
            log.warning(
                "Could not fetch tweets for @%s from any Nitter instance. "
                "This is expected — Nitter availability is unreliable.",
                handle,
            )
            return []

        items: list[ContentItem] = []
        for entry in feed.entries[: source.max_items]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime.fromtimestamp(
                    mktime(entry.published_parsed), tz=timezone.utc
                )

            items.append(
                ContentItem(
                    source_name=source.name,
                    platform="twitter",
                    title=getattr(entry, "title", "Tweet"),
                    url=getattr(entry, "link", ""),
                    content_text=_strip_html(getattr(entry, "summary", "")),
                    published=published,
                )
            )

        return items
