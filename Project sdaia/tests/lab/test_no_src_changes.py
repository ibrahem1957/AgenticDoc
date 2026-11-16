from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _imports(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_lab_does_not_import_src_and_core_does_not_import_streamlit() -> None:
    for path in (ROOT / "lab").rglob("*.py"):
        imported = _imports(path)
        assert not any(name == "src" or name.startswith("src.") for name in imported), (
            path
        )
        if (ROOT / "lab" / "core") in path.parents:
            assert not any(
                name == "streamlit" or name.startswith("streamlit.")
                for name in imported
            ), path


def test_src_does_not_import_lab() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        assert not any(
            name == "lab" or name.startswith("lab.") for name in _imports(path)
        ), path


def test_e1_configuration_has_no_openrouter_or_network_settings() -> None:
    paths = [
        ROOT / "lab" / "config" / "lab.toml",
        ROOT / "lab" / "config" / "adapters.toml",
        ROOT / "lab" / "core" / "settings.py",
        ROOT / "lab" / "app" / "Home.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)
    for forbidden in ("openrouter", "api_key", "require_zdr", "cost_per_run"):
        assert forbidden not in combined
