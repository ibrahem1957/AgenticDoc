from __future__ import annotations

import hashlib
import io
import secrets
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

import pypdfium2 as pdfium
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from lab.core.models import LabDocument, PageTag
from lab.core.settings import LabSettings
from lab.core.workspace import WorkspaceManager


class IngestError(ValueError):
    pass


MAGIC_TYPES = (
    (b"%PDF-", "pdf", ".pdf"),
    (b"\x89PNG\r\n\x1a\n", "image", ".png"),
    (b"\xff\xd8\xff", "image", ".jpg"),
    (b"II*\x00", "image", ".tif"),
    (b"MM\x00*", "image", ".tif"),
    (b"RIFF", "image", ".webp"),
)


def detect_kind(header: bytes) -> tuple[str, str]:
    for magic, kind, extension in MAGIC_TYPES:
        if header.startswith(magic):
            if extension == ".webp" and header[8:12] != b"WEBP":
                continue
            return kind, extension
    raise IngestError("Unsupported file type; expected PDF, PNG, JPEG, TIFF, or WebP")


def sanitize_filename(filename: str) -> str:
    value = unicodedata.normalize("NFC", filename)
    value = "".join(
        char
        for char in value
        if unicodedata.category(char) != "Cc"
        and not ("\u202a" <= char <= "\u202e")
        and not ("\u2066" <= char <= "\u2069")
    )
    value = value.replace("/", "_").replace("\\", "_").strip(" .")
    return (value or "document")[:255]


def _write_stream(source: BinaryIO, target: Path, max_bytes: int) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    header = b""
    with target.open("wb") as output:
        while chunk := source.read(1024 * 1024):
            if not isinstance(chunk, bytes):
                raise IngestError("Upload stream must return bytes")
            if len(header) < 16:
                header += chunk[: 16 - len(header)]
            size += len(chunk)
            if size > max_bytes:
                output.close()
                target.unlink(missing_ok=True)
                raise IngestError("File exceeds configured size limit")
            digest.update(chunk)
            output.write(chunk)
    if size == 0:
        target.unlink(missing_ok=True)
        raise IngestError("File is empty")
    return size, digest.hexdigest()


def _pdf_details(
    path: Path, max_pages: int
) -> tuple[int, list[tuple[float, float]], list[bool], str | None, str | None]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise IngestError("Encrypted PDFs are not supported")
        metadata = reader.metadata or {}
        producer = _metadata_text(metadata.get("/Producer"))
        creator = _metadata_text(metadata.get("/Creator"))
        document = pdfium.PdfDocument(path)
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"Malformed or unreadable PDF: {type(exc).__name__}") from exc
    try:
        page_count = len(document)
        if page_count <= 0:
            raise IngestError("PDF has no pages")
        if page_count > max_pages:
            raise IngestError(f"PDF exceeds the {max_pages}-page limit")
        sizes: list[tuple[float, float]] = []
        text_layers: list[bool] = []
        for index in range(page_count):
            page = document[index]
            sizes.append(tuple(float(value) for value in page.get_size()))
            textpage = page.get_textpage()
            text_layers.append(textpage.count_chars() > 0)
            textpage.close()
            page.close()
        return page_count, sizes, text_layers, producer, creator
    finally:
        document.close()


def _metadata_text(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None


def _image_details(path: Path) -> tuple[list[tuple[float, float]], str]:
    Image.MAX_IMAGE_PIXELS = 50_000_000
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return [(float(image.width), float(image.height))], (
                image.format or ""
            ).lower()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise IngestError("Malformed or unsafe image") from exc


class IngestService:
    def __init__(self, manager: WorkspaceManager, settings: LabSettings):
        self.manager = manager
        self.settings = settings

    def _documents(self, workspace_id: str) -> list[LabDocument]:
        docs_dir = self.manager.path(workspace_id) / "docs"
        documents: list[LabDocument] = []
        for metadata in docs_dir.glob("doc_*/document.json"):
            try:
                documents.append(
                    LabDocument.model_validate_json(
                        metadata.read_text(encoding="utf-8")
                    )
                )
            except (OSError, ValueError):
                continue
        return sorted(documents, key=lambda item: item.uploaded_at)

    def list_documents(self, workspace_id: str) -> list[LabDocument]:
        self.manager.attach(workspace_id)
        return self._documents(workspace_id)

    def ingest(self, workspace_id: str, source: BinaryIO, filename: str) -> LabDocument:
        self.manager.attach(workspace_id)
        if len(self._documents(workspace_id)) >= self.settings.max_documents:
            raise IngestError("Workspace document limit reached")
        prefix = source.read(16)
        if not prefix:
            raise IngestError("File is empty")
        try:
            source.seek(0)
        except (AttributeError, OSError):
            source = io.BytesIO(prefix + source.read())
        kind, extension = detect_kind(prefix)
        doc_id = f"doc_{secrets.token_urlsafe(12)}"
        doc_dir = self.manager.path(workspace_id) / "docs" / doc_id
        doc_dir.mkdir(parents=True)
        original_path = doc_dir / f"original{extension}"
        try:
            size, sha256 = _write_stream(
                source, original_path, self.settings.max_file_mb * 1024 * 1024
            )
            if kind == "pdf":
                page_count, page_sizes, has_text, producer, creator = _pdf_details(
                    original_path, self.settings.max_pages
                )
            else:
                page_sizes, _ = _image_details(original_path)
                page_count, has_text, producer, creator = 1, None, None, None
            document = LabDocument(
                doc_id=doc_id,
                display_name=sanitize_filename(filename),
                kind=kind,
                sha256=sha256,
                size_bytes=size,
                page_count=page_count,
                page_sizes=page_sizes,
                has_text_layer=has_text,
                pdf_producer=producer,
                pdf_creator=creator,
                page_tags={},
                uploaded_at=datetime.now(timezone.utc),
            )
            WorkspaceManager.atomic_write_json(
                doc_dir / "document.json", document.model_dump(mode="json")
            )
            return document
        except Exception:
            import shutil

            shutil.rmtree(doc_dir, ignore_errors=True)
            raise

    def original_path(self, workspace_id: str, doc_id: str) -> Path:
        doc_dir = (self.manager.path(workspace_id) / "docs" / doc_id).resolve()
        if not doc_dir.is_relative_to(self.manager.path(workspace_id) / "docs"):
            raise IngestError("Invalid document ID")
        matches = list(doc_dir.glob("original.*"))
        if len(matches) != 1:
            raise IngestError("Document content is missing")
        return matches[0]

    def get(self, workspace_id: str, doc_id: str) -> LabDocument:
        docs_root = (self.manager.path(workspace_id) / "docs").resolve()
        doc_dir = (docs_root / doc_id).resolve()
        if not doc_dir.is_relative_to(docs_root):
            raise IngestError("Invalid document ID")
        metadata = doc_dir / "document.json"
        if not metadata.is_file():
            raise IngestError("Document not found")
        return LabDocument.model_validate_json(metadata.read_text(encoding="utf-8"))

    def delete(self, workspace_id: str, doc_id: str) -> None:
        import shutil

        doc_dir = (self.manager.path(workspace_id) / "docs" / doc_id).resolve()
        if not doc_dir.is_relative_to(self.manager.path(workspace_id) / "docs"):
            raise IngestError("Invalid document ID")
        shutil.rmtree(doc_dir, ignore_errors=True)

    def set_page_tags(
        self, workspace_id: str, doc_id: str, page: int, tags: list[PageTag]
    ) -> LabDocument:
        document = self.get(workspace_id, doc_id)
        if page < 1 or page > document.page_count:
            raise IngestError("Page is out of range")
        document.page_tags[page] = list(dict.fromkeys(tags))
        metadata = self.manager.path(workspace_id) / "docs" / doc_id / "document.json"
        WorkspaceManager.atomic_write_json(metadata, document.model_dump(mode="json"))
        return document

    def render_page(self, workspace_id: str, doc_id: str, page: int) -> Path:
        document = self.get(workspace_id, doc_id)
        if page < 1 or page > document.page_count:
            raise IngestError("Page is out of range")
        page_path = (
            self.manager.path(workspace_id)
            / "docs"
            / doc_id
            / "pages"
            / f"p{page:04d}.png"
        )
        if page_path.is_file():
            return page_path
        page_path.parent.mkdir(parents=True, exist_ok=True)
        source = self.original_path(workspace_id, doc_id)
        if document.kind == "image":
            with Image.open(source) as image:
                rendered = image.convert("RGB")
                if max(rendered.size) > 4000:
                    rendered.thumbnail((4000, 4000), Image.Resampling.LANCZOS)
                rendered.save(page_path, "PNG")
            return page_path
        pdf = pdfium.PdfDocument(source)
        try:
            pdf_page = pdf[page - 1]
            width, height = pdf_page.get_size()
            scale = self.settings.viewer_dpi / 72
            longest = max(width, height) * scale
            if longest > 4000:
                scale *= 4000 / longest
            bitmap = pdf_page.render(scale=scale)
            bitmap.to_pil().save(page_path, "PNG")
            bitmap.close()
            pdf_page.close()
        finally:
            pdf.close()
        return page_path
