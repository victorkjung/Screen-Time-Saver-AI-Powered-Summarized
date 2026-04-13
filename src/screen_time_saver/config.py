"""Configuration loading and validation via Pydantic + YAML."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator


class SourceConfig(BaseModel):
    """A single content source the user wants to follow."""

    name: str
    platform: Literal["youtube", "rss", "twitter"]
    channel_url: str | None = None
    feed_url: str | None = None
    handle: str | None = None
    max_items: int = 5

    @model_validator(mode="after")
    def _check_platform_fields(self) -> "SourceConfig":
        if self.platform == "youtube" and not self.channel_url:
            raise ValueError("YouTube sources require 'channel_url'")
        if self.platform == "rss" and not self.feed_url:
            raise ValueError("RSS sources require 'feed_url'")
        if self.platform == "twitter" and not self.handle:
            raise ValueError("Twitter sources require 'handle'")
        return self


class OutputConfig(BaseModel):
    """Settings for generated output files."""

    directory: str = "./output"
    audio_format: Literal["mp3"] = "mp3"
    voice: str = "en-US-AndrewMultilingualNeural"
    speech_rate: str = "+10%"
    max_audio_minutes: int = 10


class SummarizerConfig(BaseModel):
    """Settings for the Claude-powered summariser."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    style: Literal["podcast", "newsletter", "briefing"] = "podcast"


class AppConfig(BaseModel):
    """Top-level application configuration."""

    anthropic_api_key: str
    sources: list[SourceConfig]
    output: OutputConfig = OutputConfig()
    summarizer: SummarizerConfig = SummarizerConfig()


def load_config(path: Path) -> AppConfig:
    """Load and validate a YAML configuration file.

    Supports ``${ENV_VAR}`` interpolation in the ``anthropic_api_key`` field.
    """
    with open(path) as fh:
        raw = yaml.safe_load(fh)

    # Environment-variable interpolation for the API key.
    key = raw.get("anthropic_api_key", "")
    if isinstance(key, str):
        raw["anthropic_api_key"] = os.path.expandvars(key)

    return AppConfig(**raw)
