from pathlib import Path

import pytest
from pydantic import ValidationError

from screen_time_saver.config import TwilioConfig, load_config
from screen_time_saver.delivery.telegram_bot import _escape_markdown
from screen_time_saver.delivery.twilio_call import deliver_via_twilio
from screen_time_saver.models import Digest


def test_load_config_empty_yaml_raises_validation_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(config_path)


@pytest.mark.asyncio
async def test_twilio_requires_public_audio_base_url(tmp_path: Path) -> None:
    audio_path = tmp_path / "digest.mp3"
    audio_path.write_bytes(b"fake-mp3")
    digest = Digest(
        title="Daily Digest",
        sections=[],
        full_script="hello",
        estimated_read_minutes=1,
    )
    config = TwilioConfig(
        enabled=True,
        account_sid="sid",
        auth_token="token",
        from_phone="+15551234567",
        to_phone="+15557654321",
        audio_base_url=None,
    )

    with pytest.raises(ValueError, match="audio_base_url"):
        await deliver_via_twilio(digest, audio_path, config)


def test_escape_markdown_v2_special_characters() -> None:
    assert _escape_markdown("Title_[v1](test)!") == "Title\\_\\[v1\\]\\(test\\)\\!"
