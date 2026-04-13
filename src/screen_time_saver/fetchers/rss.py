"""RSS feed fetcher using feedparser."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from time import mktime

import feedparser

from screen_time_saver.config import SourceConfig
from screen_time_saver.fetchers.base import BaseFetcher
from screen_time_saver.models import ContentItem

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    """Naively strip HTML tags and collapse whitespace."""
    text = _TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


class RSSFetcher(BaseFetcher):
    """Fetch and parse any standard RSS / Atom feed."""

    async def fetch(self, source: SourceConfig) -> list[ContentItem]:
        feed = feedparser.parse(source.feed_url)
        items: list[ContentItem] = []

        for entry in feed.entries[: source.max_items]:
            # Prefer full content; fall back to summary.
            raw_body = ""
            if hasattr(entry, "content") and entry.content:
                raw_body = entry.content[0].get("value", "")
            if not raw_body:
                raw_body = getattr(entry, "summary", "")

            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime.fromtimestamp(
                    mktime(entry.published_parsed), tz=timezone.utc
                )

            items.append(
                ContentItem(
                    source_name=source.name,
                    platform="rss",
                    title=getattr(entry, "title", "(untitled)"),
                    url=getattr(entry, "link", ""),
                    content_text=_strip_html(raw_body),
                    published=published,
                )
            )

        return items
