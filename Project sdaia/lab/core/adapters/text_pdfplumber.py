from __future__ import annotations

import time
from pathlib import Path

import pdfplumber

from lab.core.adapters.base import LocalTextAdapter, text_status
from lab.core.models import AdapterInfo, PageResult, RunContext, TextBlock

ADAPTER_VERSION = "3"


def _word_blocks(words: list[dict], tolerance: float) -> list[TextBlock]:
    lines: list[list[dict]] = []
    for word in words:
        line = next(
            (
                candidate
                for candidate in lines
                if abs(float(candidate[0]["top"]) - float(word["top"])) <= tolerance
            ),
            None,
        )
        if line is None:
            line = []
            lines.append(line)
        line.append(word)
    blocks: list[TextBlock] = []
    for order, line in enumerate(lines):
        blocks.append(
            TextBlock(
                order=order,
                text=" ".join(str(word["text"]) for word in line),
                bbox=(
                    min(float(word["x0"]) for word in line),
                    min(float(word["top"]) for word in line),
                    max(float(word["x1"]) for word in line),
                    max(float(word["bottom"]) for word in line),
                ),
            )
        )
    return blocks


class PdfPlumberAdapter(LocalTextAdapter):
    def run(
        self, pdf_path: Path, pages: list[int], params: dict, ctx: RunContext
    ) -> list[PageResult]:
        results: list[PageResult] = []
        with pdfplumber.open(pdf_path) as document:
            for page_number in pages:
                # Extraction timing includes page loading (E1-A review, M2).
                started = time.perf_counter()
                cpu_started = time.process_time()
                page = document.pages[page_number - 1]
                text = (
                    page.extract_text(
                        layout=bool(params.get("layout", False)),
                        x_tolerance=float(params.get("x_tolerance", 3.0)),
                    )
                    or ""
                )
                elapsed = (time.perf_counter() - started) * 1000
                extraction_cpu = (time.process_time() - cpu_started) * 1000
                overlay_started = time.perf_counter()
                blocks = _word_blocks(
                    page.extract_words(), float(params.get("line_tolerance", 3.0))
                )
                overlay_ms = (time.perf_counter() - overlay_started) * 1000
                results.append(
                    PageResult(
                        page=page_number,
                        text=text,
                        blocks=blocks,
                        status=text_status(text),
                        error=None,
                        elapsed_ms=elapsed,
                        overlay_ms=overlay_ms,
                        extraction_cpu_ms=extraction_cpu,
                    )
                )
        return results


def create_adapter(info: AdapterInfo) -> PdfPlumberAdapter:
    return PdfPlumberAdapter(info)
