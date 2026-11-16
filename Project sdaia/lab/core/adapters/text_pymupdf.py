from __future__ import annotations

import time
from pathlib import Path

import pymupdf

from lab.core.adapters.base import LocalTextAdapter, text_status
from lab.core.models import AdapterInfo, PageResult, RunContext, TextBlock

ADAPTER_VERSION = "3"


class PyMuPDFAdapter(LocalTextAdapter):
    def run(
        self, pdf_path: Path, pages: list[int], params: dict, ctx: RunContext
    ) -> list[PageResult]:
        document = pymupdf.open(pdf_path)
        results: list[PageResult] = []
        try:
            for page_number in pages:
                # Extraction timing includes page loading (E1-A review, M2).
                started = time.perf_counter()
                cpu_started = time.process_time()
                page = document[page_number - 1]
                text = page.get_text("text", sort=bool(params.get("sort", False)))
                elapsed = (time.perf_counter() - started) * 1000
                extraction_cpu = (time.process_time() - cpu_started) * 1000
                overlay_started = time.perf_counter()
                raw_blocks = page.get_text(
                    "blocks", sort=bool(params.get("sort", False))
                )
                blocks = [
                    TextBlock(
                        order=index,
                        text=str(block[4]),
                        bbox=(
                            float(block[0]),
                            float(block[1]),
                            float(block[2]),
                            float(block[3]),
                        ),
                    )
                    for index, block in enumerate(raw_blocks)
                    if len(block) < 7 or block[6] == 0
                ]
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
        finally:
            document.close()
        return results


def create_adapter(info: AdapterInfo) -> PyMuPDFAdapter:
    return PyMuPDFAdapter(info)
