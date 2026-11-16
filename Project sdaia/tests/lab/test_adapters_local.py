from __future__ import annotations

from pathlib import Path

import pytest

from lab.core.adapters.registry import AdapterRegistry
from lab.core.adapters.base import text_status
from lab.core.models import RunContext


@pytest.mark.parametrize(
    "adapter_id", ["text.pymupdf", "text.pypdfium2", "text.pdfplumber", "text.pypdf"]
)
def test_each_local_adapter_extracts_text(data_dir: Path, adapter_id: str) -> None:
    registry = AdapterRegistry()
    adapter = registry.build(adapter_id)
    results = adapter.run(
        data_dir / "text.pdf",
        [1],
        adapter.info.params,
        RunContext(workspace_id="ws_test"),
    )
    assert len(results) == 1
    assert results[0].status == "ok"
    assert "Synthetic" in results[0].text


@pytest.mark.parametrize(
    "adapter_id", ["text.pymupdf", "text.pypdfium2", "text.pdfplumber", "text.pypdf"]
)
def test_image_only_pdf_is_empty(data_dir: Path, adapter_id: str) -> None:
    registry = AdapterRegistry()
    adapter = registry.build(adapter_id)
    results = adapter.run(
        data_dir / "image_only.pdf",
        [1],
        adapter.info.params,
        RunContext(workspace_id="ws_test"),
    )
    assert results[0].status == "empty"


def test_registry_marks_disabled_and_missing_dependency() -> None:
    registry = AdapterRegistry(
        [
            {
                "id": "text.off",
                "task": "text",
                "label": "Off",
                "kind": "api",
                "module": "missing",
                "library": "none",
                "license": "none",
                "enabled": False,
            },
            {
                "id": "text.missing",
                "task": "text",
                "label": "Missing",
                "kind": "local",
                "module": "missing.module",
                "library": "missing-package",
                "license": "none",
                "enabled": True,
            },
        ]
    )
    assert not registry.get("text.off").info.available
    assert not registry.get("text.missing").info.available
    with pytest.raises(RuntimeError):
        registry.build("text.off")


@pytest.mark.parametrize("text", ["", " ", "\n\t", "\u00a0"])
def test_whitespace_only_text_is_empty(text: str) -> None:
    assert text_status(text) == "empty"
