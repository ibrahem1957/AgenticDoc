from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LAB_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LabSettings:
    tmp_dir: str
    workspace_ttl_hours: float
    max_file_mb: int
    max_pages: int
    max_documents: int
    viewer_dpi: int
    adapter_timeout_s: int
    e2_candidate_cer: float


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_settings() -> LabSettings:
    raw = _read_toml(LAB_DIR / "config" / "lab.toml")
    raw["tmp_dir"] = os.getenv("LAB_TMP_DIR", raw.get("tmp_dir", ""))
    return LabSettings(**raw)


def load_adapter_config() -> list[dict[str, Any]]:
    return _read_toml(LAB_DIR / "config" / "adapters.toml").get("adapters", [])
