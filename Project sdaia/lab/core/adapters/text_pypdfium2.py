from __future__ import annotations

import time
from pathlib import Path

import pypdfium2 as pdfium

from lab.core.adapters.base import LocalTextAdapter, text_status
from lab.core.models import AdapterInfo, PageResult, RunContext, TextBlock

ADAPTER_VERSION = "3"


def _line_blocks(textpage, page_height: float, tolerance: float) -> list[TextBlock]:
    lines: list[dict] = []
    for index in range(textpage.count_chars()):
        char = textpage.get_text_range(index, 1)
        if not char or char in "\r\n":
            continue
        try:
            left, bottom, right, top = (
                float(value) for value in textpage.get_charbox(index)
            )
        except Exception:
            continue
        y = (top + bottom) / 2
        line = next(
            (candidate for candidate in lines if abs(candidate["y"] - y) <= tolerance),
            None,
        )
        if line is None:
            line = {"y": y, "chars": [], "bbox": [left, bottom, right, top]}
            lines.append(line)
        line["chars"].append((index, char))
        line["bbox"][0] = min(line["bbox"][0], left)
        line["bbox"][1] = min(line["bbox"][1], bottom)
        line["bbox"][2] = max(line["bbox"][2], right)
        line["bbox"][3] = max(line["bbox"][3], top)
    blocks: list[TextBlock] = []
    for order, line in enumerate(
        sorted(lines, key=lambda item: min(index for index, _ in item["chars"]))
    ):
        chars = "".join(char for _, char in sorted(line["chars"]))
        left, bottom, right, top = line["bbox"]
        blocks.append(
            TextBlock(
                order=order,
                text=chars,
                bbox=(left, page_height - top, right, page_height - bottom),
            )
        )
    return blocks


class PdfiumAdapter(LocalTextAdapter):
    def run(
        self, pdf_path: Path, pages: list[int], params: dict, ctx: RunContext
    ) -> list[PageResult]:
        document = pdfium.PdfDocument(pdf_path)
        results: list[PageResult] = []
        try:
            for page_number in pages:
                # Extraction timing includes page loading and text-page creation:
                # pdfium parses the characters in get_textpage(), so excluding it
                # would understate this extractor's cost (E1-A review, M2).
                started = time.perf_counter()
                cpu_started = time.process_time()
                page = document[page_number - 1]
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                elapsed = (time.perf_counter() - started) * 1000
                extraction_cpu = (time.process_time() - cpu_started) * 1000
                overlay_started = time.perf_counter()
                _, page_height = page.get_size()
                blocks = _line_blocks(
                    textpage,
                    float(page_height),
                    float(params.get("line_tolerance", 3.0)),
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
                textpage.close()
                page.close()
        finally:
            document.close()
        return results


def create_adapter(info: AdapterInfo) -> PdfiumAdapter:
    return PdfiumAdapter(info)
