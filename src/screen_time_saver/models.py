"""Shared data models that flow between all layers of the application."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """A single piece of content fetched from a social media source."""

    source_name: str
    platform: str
    title: str
    url: str
    content_text: str = Field(description="Raw text — transcript, article body, or tweet text")
    published: datetime | None = None
    duration_seconds: int | None = None


class DigestSection(BaseModel):
    """One section of the summarised digest (maps to one source)."""

    source_name: str
    headline: str
    summary: str
    key_points: list[str]
    source_url: str


class Digest(BaseModel):
    """The full AI-generated digest ready for narration."""

    title: str
    generated_at: datetime = Field(default_factory=datetime.now)
    sections: list[DigestSection]
    full_script: str = Field(description="TTS-ready narration script")
    estimated_read_minutes: float


class TimestampedSegment(BaseModel):
    """A timed text segment used for SRT / caption generation."""

    start_ms: int
    end_ms: int
    text: str
