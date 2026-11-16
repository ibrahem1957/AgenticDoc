from __future__ import annotations

import json
import shutil
from pathlib import Path

from lab.core.bench import run_bench


def test_bench_runs_local_adapters_and_labels_timing_columns(
    settings, data_dir: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("LAB_TMP_DIR", settings.tmp_dir)
    fixtures = tmp_path / "fixtures"
    (fixtures / "synthetic").mkdir(parents=True)
    shutil.copy(data_dir / "text.pdf", fixtures / "synthetic" / "document_test.pdf")
    output = tmp_path / "bench"

    assert run_bench(fixtures, output) == 0

    results = json.loads((output / "results.json").read_text(encoding="utf-8"))
    adapters = {run["adapter"] for run in results["runs"]}
    assert adapters == {"text.pymupdf", "text.pypdfium2", "text.pdfplumber", "text.pypdf"}
    assert all(run["status"] == "ok" for run in results["runs"])
    assert all(run["startup_ms"] >= 0 and run["overlay_ms"] >= 0 for run in results["runs"])

    report = (output / "report.md").read_text(encoding="utf-8")
    assert "Extraction wall ms" in report
    assert "Startup ms" in report
    assert "Overlay ms" in report
    assert "not an extractor verdict" in report
    for banned in ("winner", "best ocr", "recommended pipeline"):
        assert banned not in report.lower()
    # Bench workspaces are temporary and removed after each fixture.
    assert not any(Path(settings.tmp_dir).glob("ws_*"))
