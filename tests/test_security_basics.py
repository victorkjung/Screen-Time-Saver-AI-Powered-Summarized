from pathlib import Path

import pytest
from pydantic import ValidationError

from screen_time_saver.config import load_config


def test_load_config_empty_yaml_raises_validation_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(config_path)
