from __future__ import annotations

import time
from pathlib import Path

from pypdf import PdfReader

from lab.core.adapters.base import LocalTextAdapter, text_status
from lab.core.models import AdapterInfo, PageResult, RunContext

ADAPTER_VERSION = "3"


class PyPdfAdapter(LocalTextAdapter):
    def run(
        self, pdf_path: Path, pages: list[int], params: dict, ctx: RunContext
    ) -> list[PageResult]:
        document = PdfReader(pdf_path)
        results: list[PageResult] = []
        for page_number in pages:
            started = time.perf_counter()
            cpu_started = time.process_time()
            mode = str(params.get("mode", "plain"))
            text = (
                document.pages[page_number - 1].extract_text(extraction_mode=mode) or ""
            )
            elapsed = (time.perf_counter() - started) * 1000
            extraction_cpu = (time.process_time() - cpu_started) * 1000
            results.append(
                PageResult(
                    page=page_number,
                    text=text,
                    blocks=None,
                    status=text_status(text),
                    error=None,
                    elapsed_ms=elapsed,
                    overlay_ms=0.0,
                    extraction_cpu_ms=extraction_cpu,
                )
            )
        return results


def create_adapter(info: AdapterInfo) -> PyPdfAdapter:
    return PyPdfAdapter(info)
