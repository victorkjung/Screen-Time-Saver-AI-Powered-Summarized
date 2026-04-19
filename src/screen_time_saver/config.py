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


class TwilioConfig(BaseModel):
    """Twilio outbound-call delivery settings."""

    enabled: bool = False
    account_sid: str = ""
    auth_token: str = ""
    from_phone: str = ""  # Your Twilio phone number, e.g. "+15551234567"
    to_phone: str = ""  # Destination phone number
    audio_base_url: str | None = None  # Public URL prefix for the MP3
    local_server_port: int = 8765  # Fallback local file server port


class TelegramConfig(BaseModel):
    """Telegram bot delivery settings."""

    enabled: bool = False
    bot_token: str = ""  # From @BotFather
    chat_id: str = ""  # Target chat/channel ID
    message_thread_id: int | None = None  # Optional forum topic ID (supergroups with topics)


class DeliveryConfig(BaseModel):
    """Delivery backends — how the digest reaches you."""

    twilio: TwilioConfig | None = None
    telegram: TelegramConfig | None = None


class AppConfig(BaseModel):
    """Top-level application configuration."""

    anthropic_api_key: str
    sources: list[SourceConfig]
    output: OutputConfig = OutputConfig()
    summarizer: SummarizerConfig = SummarizerConfig()
    delivery: DeliveryConfig = DeliveryConfig()


def load_config(path: Path) -> AppConfig:
    """Load and validate a YAML configuration file.

    Supports ``${ENV_VAR}`` interpolation in the ``anthropic_api_key`` field.
    """
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    # Environment-variable interpolation for secrets.
    key = raw.get("anthropic_api_key", "")
    if isinstance(key, str):
        raw["anthropic_api_key"] = os.path.expandvars(key)

    # Expand env vars in delivery config secrets.
    delivery = raw.get("delivery") or {}
    for backend in ("twilio", "telegram"):
        section = delivery.get(backend) or {}
        for field in ("account_sid", "auth_token", "bot_token"):
            val = section.get(field, "")
            if isinstance(val, str):
                section[field] = os.path.expandvars(val)

    return AppConfig(**raw)
