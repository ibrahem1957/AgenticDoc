from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from lab.core.adapters.registry import AdapterRegistry
from lab.core.ingest import IngestService
from lab.core.runner import LabRunner
from lab.core.workspace import WorkspaceManager


def _registry(
    behavior: str,
    module: str = "tests.lab.stub_adapters",
    implementation_version: str | None = None,
) -> AdapterRegistry:
    entry = {
        "id": "text.stub",
        "task": "text",
        "label": "Stub",
        "kind": "local",
        "module": module,
        "library": "pytest",
        "license": "MIT",
        "enabled": True,
        "preselected": True,
        "supports_blocks": False,
        "params": {"behavior": behavior},
    }
    if implementation_version is not None:
        entry["implementation_version"] = implementation_version
    return AdapterRegistry([entry])


def _document(settings, data_dir: Path):
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    service = IngestService(manager, settings)
    with (data_dir / "text.pdf").open("rb") as handle:
        document = service.ingest(workspace.workspace_id, handle, "text.pdf")
    return manager, workspace, service, document


def test_runner_cache_bypass_repeats_and_progress(settings, data_dir: Path) -> None:
    manager, workspace, service, document = _document(settings, data_dir)
    runner = LabRunner(manager, settings, _registry("ok"))
    path = service.original_path(workspace.workspace_id, document.doc_id)
    first = runner.run_local(
        workspace.workspace_id, document, path, "text.stub", [1], repeats=3
    )
    assert first.status == "ok"
    assert len(first.repeat_timings) == 3
    cached = runner.run_local(workspace.workspace_id, document, path, "text.stub", [1])
    assert cached.cache_hit
    bypassed = runner.run_local(
        workspace.workspace_id, document, path, "text.stub", [1], bypass_cache=True
    )
    assert not bypassed.cache_hit
    progress = []
    results = runner.run_many(
        workspace.workspace_id,
        document,
        path,
        ["text.stub"],
        [1],
        lambda *args: progress.append(args),
    )
    assert results and progress[0][:2] == (1, 1)


def test_runner_timeout_and_crash_are_isolated(settings, data_dir: Path) -> None:
    manager, workspace, service, document = _document(settings, data_dir)
    path = service.original_path(workspace.workspace_id, document.doc_id)
    timeout = LabRunner(manager, settings, _registry("sleep")).run_local(
        workspace.workspace_id, document, path, "text.stub", [1]
    )
    assert timeout.status == "timeout"
    crash = LabRunner(manager, settings, _registry("crash")).run_local(
        workspace.workspace_id, document, path, "text.stub", [1]
    )
    assert crash.status == "error"
    assert "synthetic adapter crash" in (crash.error or "")


def test_large_child_payload_is_received_without_deadlock(
    settings, data_dir: Path
) -> None:
    settings = replace(settings, adapter_timeout_s=20)
    manager, workspace, service, document = _document(settings, data_dir)
    path = service.original_path(workspace.workspace_id, document.doc_id)
    started = time.perf_counter()
    result = LabRunner(manager, settings, _registry("large")).run_local(
        workspace.workspace_id, document, path, "text.stub", [1, 2, 3]
    )
    assert time.perf_counter() - started < settings.adapter_timeout_s
    assert result.status == "ok"
    assert [len(page.text) for page in result.pages] == [600_000] * 3
    assert all(page.text == "ن" * 600_000 for page in result.pages)


def test_import_time_is_separate_from_extraction_time(settings, data_dir: Path) -> None:
    settings = replace(settings, adapter_timeout_s=10)
    manager, workspace, service, document = _document(settings, data_dir)
    result = LabRunner(
        manager,
        settings,
        _registry("ok", module="tests.lab.slow_import_adapter"),
    ).run_local(
        workspace.workspace_id,
        document,
        service.original_path(workspace.workspace_id, document.doc_id),
        "text.stub",
        [1],
    )
    assert result.status == "ok"
    assert result.wall_ms < 500
    assert result.startup_ms >= 900
    assert result.overlay_ms == 0


def test_document_open_counts_as_extraction_time(settings, data_dir: Path) -> None:
    # Regression for the E1-A self-review: timing must not start after page or
    # document loading, otherwise extractors that parse at open time look faster.
    settings = replace(settings, adapter_timeout_s=10)
    manager, workspace, service, document = _document(settings, data_dir)
    result = LabRunner(manager, settings, _registry("slow_open")).run_local(
        workspace.workspace_id,
        document,
        service.original_path(workspace.workspace_id, document.doc_id),
        "text.stub",
        [1],
    )
    assert result.status == "ok"
    assert result.wall_ms >= 350
    assert result.overlay_ms == 0


def test_overlay_time_is_excluded_from_extraction_time(
    settings, data_dir: Path
) -> None:
    settings = replace(settings, adapter_timeout_s=10)
    manager, workspace, service, document = _document(settings, data_dir)
    result = LabRunner(manager, settings, _registry("slow_overlay")).run_local(
        workspace.workspace_id,
        document,
        service.original_path(workspace.workspace_id, document.doc_id),
        "text.stub",
        [1],
    )
    assert result.status == "ok"
    assert result.overlay_ms >= 350
    assert result.wall_ms < 150


def test_timeout_is_not_cached_and_second_run_executes(
    settings, data_dir: Path
) -> None:
    settings = replace(settings, adapter_timeout_s=0.3)
    manager, workspace, service, document = _document(settings, data_dir)
    runner = LabRunner(manager, settings, _registry("sleep_once"))
    path = service.original_path(workspace.workspace_id, document.doc_id)
    first = runner.run_local(workspace.workspace_id, document, path, "text.stub", [1])
    second = runner.run_local(workspace.workspace_id, document, path, "text.stub", [1])
    assert first.status == "timeout"
    assert not first.cache_hit
    assert second.status == "ok"
    assert not second.cache_hit


def test_cache_key_includes_lab_and_adapter_implementation_versions(
    settings, data_dir: Path, monkeypatch
) -> None:
    manager, workspace, _, document = _document(settings, data_dir)
    runner = LabRunner(manager, settings, _registry("ok"))
    adapter = runner.registry.get("text.stub").info
    original = runner._cache_key(document, adapter, [1], adapter.params, "raw")
    changed_adapter = runner._cache_key(
        document,
        adapter.model_copy(update={"implementation_version": "next"}),
        [1],
        adapter.params,
        "raw",
    )
    monkeypatch.setattr("lab.core.runner.__version__", "next")
    changed_lab = runner._cache_key(document, adapter, [1], adapter.params, "raw")
    assert len({original, changed_adapter, changed_lab}) == 3


def test_deep_windows_cache_path_remains_short(
    settings, data_dir: Path, tmp_path: Path
) -> None:
    deep_root = tmp_path
    while len(str(deep_root)) < 170:
        deep_root /= "deep_path_segment_1234567890"
    deep_settings = replace(settings, tmp_dir=str(deep_root), adapter_timeout_s=10)
    manager, workspace, service, document = _document(deep_settings, data_dir)
    runner = LabRunner(manager, deep_settings, _registry("ok"))
    result = runner.run_local(
        workspace.workspace_id,
        document,
        service.original_path(workspace.workspace_id, document.doc_id),
        "text.stub",
        [1],
    )
    assert result.status == "ok"
    cache_files = list((manager.path(workspace.workspace_id) / "runs").glob("c_*.json"))
    assert len(cache_files) == 1
    assert len(cache_files[0].name) < 40


def test_runner_marks_png_not_applicable(settings, data_dir: Path) -> None:
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    service = IngestService(manager, settings)
    with (data_dir / "image.png").open("rb") as handle:
        document = service.ingest(workspace.workspace_id, handle, "image.png")
    result = LabRunner(manager, settings, _registry("ok")).run_local(
        workspace.workspace_id,
        document,
        service.original_path(workspace.workspace_id, document.doc_id),
        "text.stub",
        [1],
    )
    assert result.pages[0].status == "not_applicable"
