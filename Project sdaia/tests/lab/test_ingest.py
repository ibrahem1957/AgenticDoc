from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from lab.core.ingest import (
    IngestError,
    IngestService,
    _metadata_text,
    detect_kind,
    sanitize_filename,
)
from lab.core.workspace import WorkspaceManager


def test_magic_detection_and_filename_sanitization() -> None:
    assert detect_kind(b"%PDF-1.7") == ("pdf", ".pdf")
    assert detect_kind(b"\x89PNG\r\n\x1a\n") == ("image", ".png")
    assert sanitize_filename("../../تقرير ٢٠٢٥\u202e.pdf") == "_.._تقرير ٢٠٢٥.pdf"
    with pytest.raises(IngestError):
        detect_kind(b"not-a-document")


def test_ingest_pdf_metadata_render_tags_and_delete(settings, data_dir: Path) -> None:
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    service = IngestService(manager, settings)
    with (data_dir / "text.pdf").open("rb") as handle:
        document = service.ingest(workspace.workspace_id, handle, "تقرير ٢٠٢٥.pdf")
    assert document.kind == "pdf"
    assert document.page_count == 1
    assert document.has_text_layer == [True]
    assert "تقرير" in document.display_name
    assert document.pdf_producer
    tagged = service.set_page_tags(
        workspace.workspace_id, document.doc_id, 1, ["headings", "western_digits"]
    )
    assert tagged.page_tags[1] == ["headings", "western_digits"]
    assert service.render_page(workspace.workspace_id, document.doc_id, 1).is_file()
    assert (
        service.original_path(workspace.workspace_id, document.doc_id).name
        == "original.pdf"
    )
    service.delete(workspace.workspace_id, document.doc_id)
    assert service.list_documents(workspace.workspace_id) == []


def test_get_rejects_document_path_traversal(settings) -> None:
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    with pytest.raises(IngestError, match="Invalid document ID"):
        IngestService(manager, settings).get(workspace.workspace_id, "../outside")


def test_unusual_pdf_metadata_is_coerced_without_validation_error() -> None:
    class Unprintable:
        def __str__(self) -> str:
            raise ValueError("cannot stringify")

    assert _metadata_text(123) == "123"
    assert _metadata_text(None) is None
    assert _metadata_text(Unprintable()) is None


def test_ingest_image_and_invalid_inputs(settings, data_dir: Path) -> None:
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    service = IngestService(manager, settings)
    with (data_dir / "image.png").open("rb") as handle:
        document = service.ingest(workspace.workspace_id, handle, "image.png")
    assert document.kind == "image"
    assert service.render_page(workspace.workspace_id, document.doc_id, 1).is_file()
    with pytest.raises(IngestError, match="empty"):
        service.ingest(workspace.workspace_id, io.BytesIO(b""), "empty.pdf")
    with pytest.raises(IngestError, match="Malformed"):
        service.ingest(workspace.workspace_id, io.BytesIO(b"%PDF-broken"), "broken.pdf")


def test_large_image_render_is_capped_at_4000_pixels(settings, tmp_path: Path) -> None:
    source = tmp_path / "wide.png"
    Image.new("RGB", (5001, 10), "white").save(source)
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    service = IngestService(manager, settings)
    with source.open("rb") as handle:
        document = service.ingest(workspace.workspace_id, handle, source.name)
    rendered = service.render_page(workspace.workspace_id, document.doc_id, 1)
    with Image.open(rendered) as image:
        assert max(image.size) == 4000


def test_encrypted_pdf_rejected(settings, data_dir: Path) -> None:
    source = PdfReader(data_dir / "text.pdf")
    writer = PdfWriter()
    for page in source.pages:
        writer.add_page(page)
    writer.encrypt("secret")
    encrypted = io.BytesIO()
    writer.write(encrypted)
    encrypted.seek(0)
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    with pytest.raises(IngestError, match="Encrypted"):
        IngestService(manager, settings).ingest(
            workspace.workspace_id, encrypted, "locked.pdf"
        )


def test_size_and_page_range_guards(settings, data_dir: Path) -> None:
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    service = IngestService(manager, settings)
    tiny_settings = settings.__class__(**{**settings.__dict__, "max_file_mb": 0})
    with (
        (data_dir / "text.pdf").open("rb") as handle,
        pytest.raises(IngestError, match="size"),
    ):
        IngestService(manager, tiny_settings).ingest(
            workspace.workspace_id, handle, "large.pdf"
        )
    with (data_dir / "text.pdf").open("rb") as handle:
        document = service.ingest(workspace.workspace_id, handle, "text.pdf")
    with pytest.raises(IngestError, match="range"):
        service.render_page(workspace.workspace_id, document.doc_id, 2)
