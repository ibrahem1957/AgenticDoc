from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from lab.app.components import runs_for_page_set


PROJECT_DIR = Path(__file__).resolve().parents[2]


def test_document_metadata_display_does_not_import_pandas_or_numpy_random() -> None:
    script = """
import sys
from datetime import UTC, datetime

import streamlit as st

from lab.app.components import document_metadata_text
from lab.core.models import LabDocument

document = LabDocument(
    doc_id="doc_test",
    display_name="arabic_extraction_test.pdf",
    kind="pdf",
    size_bytes=62054,
    sha256="a" * 64,
    page_count=2,
    page_sizes=[(595.0, 842.0), (595.0, 842.0)],
    has_text_layer=[True, True],
    pdf_producer="Synthetic producer",
    pdf_creator="Synthetic creator",
    uploaded_at=datetime.now(UTC),
)
st.text(document_metadata_text(document))
assert "pandas" not in sys.modules
assert "numpy.random" not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_extraction_lab_pages_avoid_dataframe_capable_display_calls() -> None:
    page_paths = [
        PROJECT_DIR / "lab" / "app" / "Home.py",
        PROJECT_DIR / "lab" / "app" / "pages" / "1_Documents.py",
        PROJECT_DIR / "lab" / "app" / "pages" / "2_Run_Text_Extraction.py",
        PROJECT_DIR / "lab" / "app" / "pages" / "3_Compare.py",
    ]
    forbidden_calls = ("st.write(", "st.dataframe(", "st.table(", "st.data_editor(")
    for path in page_paths:
        source = path.read_text(encoding="utf-8")
        assert not any(call in source for call in forbidden_calls), path


def test_compare_uses_latest_duplicate_run_by_default() -> None:
    now = datetime.now(UTC)

    def run(adapter: str, age: int, pages: tuple[int, ...]):
        return SimpleNamespace(
            adapter=SimpleNamespace(adapter_id=adapter),
            started_at=now + timedelta(seconds=age),
            pages=[SimpleNamespace(page=page) for page in pages],
        )

    old = run("text.pymupdf", 0, (1, 2))
    latest = run("text.pymupdf", 1, (1, 2))
    other = run("text.pypdf", 2, (1, 2))
    different_pages = run("text.pymupdf", 3, (1,))
    selected = runs_for_page_set(
        [latest, different_pages, other, old], (1, 2), show_all=False
    )
    assert selected == [latest, other]
    assert runs_for_page_set(
        [latest, different_pages, other, old], (1, 2), show_all=True
    ) == [old, latest, other]
