from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from lab import __version__
from lab.core.adapters.registry import AdapterRegistry
from lab.core.models import AdapterInfo, LabDocument, PageResult, RunContext, RunResult
from lab.core.settings import LabSettings
from lab.core.workspace import WorkspaceManager


def _child_run(
    output,
    module_name: str,
    info_data: dict,
    pdf_path: str,
    pages: list[int],
    params: dict,
    workspace_id: str,
):
    startup_started = time.perf_counter()
    try:
        module = __import__(module_name, fromlist=["create_adapter"])
        adapter = module.create_adapter(AdapterInfo.model_validate(info_data))
        startup_ms = (time.perf_counter() - startup_started) * 1000
        # Extraction time = the whole adapter.run() call (document open, page
        # loading and text extraction) minus block-overlay construction. Library
        # import and adapter construction are reported separately as startup_ms.
        run_started = time.perf_counter()
        page_results = adapter.run(
            Path(pdf_path), pages, params, RunContext(workspace_id=workspace_id)
        )
        run_ms = (time.perf_counter() - run_started) * 1000
        overlay_ms = sum(item.overlay_ms or 0 for item in page_results)
        output.send(
            {
                "ok": True,
                "pages": [item.model_dump(mode="json") for item in page_results],
                "wall_ms": max(0.0, run_ms - overlay_ms),
                "cpu_ms": sum(item.extraction_cpu_ms or 0 for item in page_results),
                "startup_ms": startup_ms,
                "overlay_ms": overlay_ms,
            }
        )
    except Exception as exc:
        output.send(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "wall_ms": 0,
                "cpu_ms": None,
                "startup_ms": (time.perf_counter() - startup_started) * 1000,
                "overlay_ms": 0,
            }
        )
    finally:
        output.close()


class LabRunner:
    def __init__(
        self,
        manager: WorkspaceManager,
        settings: LabSettings,
        registry: AdapterRegistry | None = None,
    ):
        self.manager = manager
        self.settings = settings
        self.registry = registry or AdapterRegistry()

    @staticmethod
    def _cache_key(
        document: LabDocument,
        adapter: AdapterInfo,
        pages: list[int],
        params: dict,
        variant: str,
    ) -> str:
        payload = {
            "sha256": document.sha256,
            "adapter": adapter.adapter_id,
            "library_version": adapter.library_version,
            "model": adapter.model_id,
            "params": params,
            "variant": variant,
            "pages": sorted(pages),
            "lab_version": __version__,
            "adapter_implementation_version": adapter.implementation_version,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _cache_path(self, workspace_id: str, key: str) -> Path:
        return self.manager.path(workspace_id) / "runs" / f"c_{key[:24]}.json"

    @staticmethod
    def _read_cache(path: Path, key: str) -> RunResult | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("cache_key") != key:
                return None
            result = RunResult.model_validate(payload.get("result"))
            if result.status not in {"ok", "partial"}:
                return None
            return result
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _write_cache(path: Path, key: str, result: RunResult) -> None:
        if result.status in {"ok", "partial"}:
            WorkspaceManager.atomic_write_json(
                path,
                {"cache_key": key, "result": result.model_dump(mode="json")},
            )

    @staticmethod
    def _environment() -> dict[str, str]:
        return {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "lab_version": __version__,
        }

    def run_local(
        self,
        workspace_id: str,
        document: LabDocument,
        pdf_path: Path,
        adapter_id: str,
        pages: list[int],
        params: dict | None = None,
        *,
        bypass_cache: bool = False,
        repeats: int = 1,
    ) -> RunResult:
        entry = self.registry.get(adapter_id)
        if entry.info.kind != "local":
            raise ValueError("run_local accepts local adapters only")
        if document.kind != "pdf":
            page_results = [
                PageResult(
                    page=page,
                    text="",
                    blocks=None,
                    status="not_applicable",
                    error="Image inputs require OCR (Phase E2)",
                    elapsed_ms=None,
                )
                for page in pages
            ]
            return self._make_result(
                document, entry.info, page_results, "ok", None, 0, 0, False, []
            )
        effective = dict(entry.info.params)
        effective.update(params or {})
        adapter_info = entry.info.model_copy(update={"params": effective})
        key = self._cache_key(document, adapter_info, pages, effective, "raw")
        cache_path = self._cache_path(workspace_id, key)
        if cache_path.is_file() and not bypass_cache:
            cached = self._read_cache(cache_path, key)
            if cached is not None:
                return cached.model_copy(update={"cache_hit": True})

        timings: list[dict[str, float | None]] = []
        final_payload: dict | None = None
        for _ in range(max(1, repeats)):
            context = multiprocessing.get_context("spawn")
            parent_output, child_output = context.Pipe(duplex=False)
            process = context.Process(
                target=_child_run,
                args=(
                    child_output,
                    entry.module,
                    adapter_info.model_dump(mode="json"),
                    str(pdf_path),
                    pages,
                    effective,
                    workspace_id,
                ),
            )
            process.start()
            child_output.close()
            deadline = time.perf_counter() + self.settings.adapter_timeout_s
            payload = None
            while time.perf_counter() < deadline:
                remaining = deadline - time.perf_counter()
                if parent_output.poll(min(0.05, max(0, remaining))):
                    try:
                        payload = parent_output.recv()
                    except EOFError:
                        payload = None
                    break
                if not process.is_alive():
                    break
            if payload is None and process.is_alive():
                process.terminate()
                process.join(5)
                parent_output.close()
                result = self._make_result(
                    document,
                    adapter_info,
                    [],
                    "timeout",
                    "Adapter timed out",
                    0,
                    None,
                    False,
                    timings,
                    0,
                    0,
                )
                return result
            process.join(max(0, deadline - time.perf_counter()))
            if process.is_alive():
                process.terminate()
                process.join(5)
            parent_output.close()
            if payload is None:
                payload = {
                    "ok": False,
                    "error": f"Adapter process exited with code {process.exitcode}",
                    "wall_ms": 0,
                    "cpu_ms": None,
                    "startup_ms": 0,
                    "overlay_ms": 0,
                }
            timings.append(
                {
                    "wall_ms": payload.get("wall_ms", 0),
                    "cpu_ms": payload.get("cpu_ms"),
                    "startup_ms": payload.get("startup_ms", 0),
                    "overlay_ms": payload.get("overlay_ms", 0),
                }
            )
            final_payload = payload
            if not payload.get("ok"):
                break

        assert final_payload is not None
        if final_payload.get("ok"):
            page_results = [
                PageResult.model_validate(item) for item in final_payload["pages"]
            ]
            status = (
                "partial"
                if any(item.status == "error" for item in page_results)
                else "ok"
            )
            wall_ms = statistics.median(float(item["wall_ms"] or 0) for item in timings)
            cpu_values = [
                float(item["cpu_ms"]) for item in timings if item["cpu_ms"] is not None
            ]
            cpu_ms = statistics.median(cpu_values) if cpu_values else None
            startup_ms = statistics.median(
                float(item.get("startup_ms") or 0) for item in timings
            )
            overlay_ms = statistics.median(
                float(item.get("overlay_ms") or 0) for item in timings
            )
            result = self._make_result(
                document,
                adapter_info,
                page_results,
                status,
                None,
                wall_ms,
                cpu_ms,
                False,
                timings,
                startup_ms,
                overlay_ms,
            )
        else:
            result = self._make_result(
                document,
                adapter_info,
                [],
                "error",
                str(final_payload.get("error", "Adapter failed")),
                float(final_payload.get("wall_ms", 0)),
                final_payload.get("cpu_ms"),
                False,
                timings,
                float(final_payload.get("startup_ms", 0)),
                float(final_payload.get("overlay_ms", 0)),
            )
        self._write_cache(cache_path, key, result)
        return result

    def _make_result(
        self,
        document: LabDocument,
        adapter: AdapterInfo,
        pages: list[PageResult],
        status: str,
        error: str | None,
        wall_ms: float,
        cpu_ms: float | None,
        cache_hit: bool,
        timings: list[dict[str, float | None]],
        startup_ms: float = 0,
        overlay_ms: float = 0,
    ) -> RunResult:
        return RunResult(
            run_id=f"run_{os.urandom(9).hex()}",
            doc_id=document.doc_id,
            doc_sha256=document.sha256,
            adapter=adapter,
            variant="raw",
            pages=pages,
            page_mapping="exact",
            started_at=datetime.now(timezone.utc),
            wall_ms=wall_ms,
            cpu_ms=cpu_ms,
            usage=None,
            status=status,
            error=error,
            cache_hit=cache_hit,
            environment=self._environment(),
            repeat_timings=timings,
            startup_ms=startup_ms,
            overlay_ms=overlay_ms,
        )

    def run_many(
        self,
        workspace_id: str,
        document: LabDocument,
        pdf_path: Path,
        adapter_ids: list[str],
        pages: list[int],
        progress: Callable[[int, int, RunResult], None] | None = None,
    ) -> list[RunResult]:
        results: list[RunResult] = []
        for index, adapter_id in enumerate(adapter_ids, start=1):
            result = self.run_local(workspace_id, document, pdf_path, adapter_id, pages)
            results.append(result)
            if progress:
                progress(index, len(adapter_ids), result)
        return results
