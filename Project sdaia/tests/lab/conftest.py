from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from lab.core.settings import LabSettings, load_settings


@pytest.fixture
def settings(tmp_path: Path) -> LabSettings:
    return replace(
        load_settings(), tmp_dir=str(tmp_path / "workspaces"), adapter_timeout_s=2
    )


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"
