from __future__ import annotations

import time

from lab.core.adapters.base import LocalTextAdapter
from lab.core.models import AdapterInfo, PageResult

ADAPTER_VERSION = "1"


class StubAdapter(LocalTextAdapter):
    def run(self, pdf_path, pages, params, ctx):
        behavior = params.get("behavior", "ok")
        if behavior == "sleep":
            time.sleep(5)
        if behavior == "sleep_once":
            marker = ctx.workspace_id + ".sleep-once"
            marker_path = pdf_path.parent / marker
            if not marker_path.exists():
                marker_path.write_text("started", encoding="utf-8")
                time.sleep(5)
        if behavior == "crash":
            raise RuntimeError("synthetic adapter crash")
        if behavior == "slow_open":
            # Simulates an expensive document open that per-page timers don't see.
            time.sleep(0.4)
        overlay_ms = 0.0
        if behavior == "slow_overlay":
            # Simulates expensive block-overlay construction, reported as overlay_ms.
            overlay_started = time.perf_counter()
            time.sleep(0.4)
            overlay_ms = (time.perf_counter() - overlay_started) * 1000
        text = " " if behavior == "whitespace" else "stub"
        if behavior == "large":
            text = "ن" * 600_000
        return [
            PageResult(
                page=page,
                text=text,
                blocks=None,
                status="ok" if text.strip() else "empty",
                error=None,
                elapsed_ms=1,
                overlay_ms=overlay_ms / len(pages),
                extraction_cpu_ms=1,
            )
            for page in pages
        ]


def create_adapter(info: AdapterInfo) -> StubAdapter:
    return StubAdapter(info)
