from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

from lab.core.models import LabDocument, RunResult


def document_metadata_text(document: LabDocument) -> str:
    """Format document details without a dataframe-capable UI code path."""
    return "\n".join(
        (
            f"Document ID: {document.doc_id}",
            f"Type: {document.kind}",
            f"Size (bytes): {document.size_bytes}",
            f"SHA-256: {document.sha256}",
            f"Text-layer pages: {sum(document.has_text_layer or [])}",
            f"PDF producer: {document.pdf_producer or '—'}",
            f"PDF creator: {document.pdf_creator or '—'}",
        )
    )


def runs_for_page_set(
    runs: Iterable[RunResult], page_set: tuple[int, ...], *, show_all: bool
) -> list[RunResult]:
    matching = [
        run for run in runs if tuple(page.page for page in run.pages) == page_set
    ]
    matching.sort(key=lambda item: item.started_at)
    if show_all:
        return matching
    latest: dict[str, RunResult] = {}
    for run in matching:
        latest[run.adapter.adapter_id] = run
    return list(latest.values())


def text_html(
    text: str, *, monospace: bool = False, show_invisibles: bool = False
) -> str:
    if show_invisibles:
        markers = {
            "\u200c": "⟦ZWNJ⟧",
            "\u200d": "⟦ZWJ⟧",
            "\u200e": "⟦LRM⟧",
            "\u200f": "⟦RLM⟧",
            "\u00a0": "⟦NBSP⟧",
        }
        text = "".join(
            markers.get(
                char, f"⟦U+{ord(char):04X}⟧" if 0xFB50 <= ord(char) <= 0xFEFF else char
            )
            for char in text
        )
    family = "monospace" if monospace else "inherit"
    return (
        '<div dir="auto" style="white-space:pre-wrap;unicode-bidi:plaintext;'
        f'font-family:{family};border:1px solid #ddd;padding:0.75rem;min-height:12rem">'
        f"{html.escape(text)}</div>"
    )


def overlay_blocks(
    image_path: Path, document: LabDocument, result: RunResult, page: int
) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    selected = next((item for item in result.pages if item.page == page), None)
    if selected is None or not selected.blocks:
        return image
    width_points, height_points = document.page_sizes[page - 1]
    scale_x = image.width / width_points
    scale_y = image.height / height_points
    draw = ImageDraw.Draw(image)
    for block in selected.blocks:
        if block.bbox is None:
            continue
        x0, y0, x1, y1 = block.bbox
        box = (x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y)
        draw.rectangle(box, outline="#e53935", width=3)
        draw.text((box[0] + 3, box[1] + 3), str(block.order + 1), fill="#e53935")
    return image
