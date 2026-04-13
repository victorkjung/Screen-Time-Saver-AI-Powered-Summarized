"""Abstract base fetcher and factory function."""

from __future__ import annotations

from abc import ABC, abstractmethod

from screen_time_saver.config import SourceConfig
from screen_time_saver.models import ContentItem


class BaseFetcher(ABC):
    """Interface every platform fetcher must implement."""

    @abstractmethod
    async def fetch(self, source: SourceConfig) -> list[ContentItem]:
        """Return recent content items for *source*."""
        ...


def get_fetcher(platform: str) -> BaseFetcher:
    """Return the appropriate fetcher instance for *platform*."""
    # Lazy imports to keep module-level lightweight.
    if platform == "youtube":
        from screen_time_saver.fetchers.youtube import YouTubeFetcher

        return YouTubeFetcher()
    if platform == "rss":
        from screen_time_saver.fetchers.rss import RSSFetcher

        return RSSFetcher()
    if platform == "twitter":
        from screen_time_saver.fetchers.twitter import TwitterFetcher

        return TwitterFetcher()
    raise ValueError(f"Unknown platform: {platform!r}")
