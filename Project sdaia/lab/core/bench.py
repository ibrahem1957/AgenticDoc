from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab.core.adapters.registry import AdapterRegistry
from lab.core.ingest import IngestService
from lab.core.runner import LabRunner
from lab.core.settings import load_settings
from lab.core.workspace import WorkspaceManager


def run_bench(fixtures: Path, output: Path) -> int:
    settings = load_settings()
    manager = WorkspaceManager(settings)
    ingest = IngestService(manager, settings)
    registry = AdapterRegistry()
    runner = LabRunner(manager, settings, registry)
    adapter_ids = [
        entry.info.adapter_id
        for entry in registry.list("text")
        if entry.info.kind == "local" and entry.info.available
    ]
    records: list[dict] = []
    inputs = sorted(fixtures.rglob("document_*.pdf"))
    standalone_png = fixtures / "standalone_png" / "image.png"
    if standalone_png.is_file():
        inputs.append(standalone_png)
    for path in inputs:
        workspace = manager.create()
        try:
            with path.open("rb") as handle:
                document = ingest.ingest(workspace.workspace_id, handle, path.name)
            pages = list(range(1, document.page_count + 1))
            source = ingest.original_path(workspace.workspace_id, document.doc_id)
            for adapter_id in adapter_ids:
                result = runner.run_local(
                    workspace.workspace_id, document, source, adapter_id, pages
                )
                records.append(
                    {
                        "fixture": str(path.relative_to(fixtures)),
                        "adapter": adapter_id,
                        "status": result.status,
                        "page_statuses": [page.status for page in result.pages],
                        "wall_ms": result.wall_ms,
                        "cpu_ms": result.cpu_ms,
                        "startup_ms": result.startup_ms,
                        "overlay_ms": result.overlay_ms,
                        "cache_hit": result.cache_hit,
                    }
                )
        finally:
            manager.end(workspace.workspace_id)
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(
        json.dumps({"schema_version": 1, "runs": records}, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# E1-A Fixture Bench",
        "",
        "Synthetic evidence only; this is not an extractor verdict and contains no user documents.",
        "",
        "Timing columns separate text extraction from adapter startup and overlay generation.",
        "",
        "| Fixture | Adapter | Status | Page statuses | Extraction wall ms | Extraction CPU ms | Startup ms | Overlay ms |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for item in records:
        lines.append(
            f"| {item['fixture']} | {item['adapter']} | {item['status']} | {', '.join(item['page_statuses'])} | {item['wall_ms']:.2f} | {item['cpu_ms'] or 0:.2f} | {item['startup_ms']:.2f} | {item['overlay_ms']:.2f} |"
        )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Completed {len(records)} local adapter runs; report: {output / 'report.md'}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    return run_bench(arguments.fixtures.resolve(), arguments.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
