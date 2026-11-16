from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from lab.core.adapters.registry import AdapterRegistry
from lab.core.ingest import IngestService
from lab.core.runner import LabRunner
from lab.core.workspace import WorkspaceManager


PROJECT_DIR = Path(__file__).resolve().parents[2]
PAGES_DIR = PROJECT_DIR / "lab" / "app" / "pages"


def _page(name: str, workspace_id: str) -> AppTest:
    app = AppTest.from_file(PAGES_DIR / name, default_timeout=30)
    app.session_state["workspace_id"] = workspace_id
    return app.run()


def test_documents_run_and_compare_without_dataframe_import_path(
    settings, monkeypatch
) -> None:
    monkeypatch.setenv("LAB_TMP_DIR", settings.tmp_dir)
    manager = WorkspaceManager(settings)
    workspace = manager.create()
    ingest = IngestService(manager, settings)
    fixture = PROJECT_DIR / "tests" / "lab" / "data" / "text.pdf"
    try:
        with fixture.open("rb") as handle:
            ingest.ingest(workspace.workspace_id, handle, fixture.name)
        registry = AdapterRegistry()
        runner = LabRunner(manager, settings, registry)
        document = ingest.list_documents(workspace.workspace_id)[0]
        source = ingest.original_path(workspace.workspace_id, document.doc_id)
        for entry in registry.list("text"):
            if entry.info.kind != "local" or not entry.info.available:
                continue
            result = runner.run_local(
                workspace.workspace_id,
                document,
                source,
                entry.info.adapter_id,
                [1],
            )
            WorkspaceManager.atomic_write_json(
                manager.path(workspace.workspace_id) / "runs" / f"{result.run_id}.json",
                result.model_dump(mode="json"),
            )
        assert (
            len(
                list((manager.path(workspace.workspace_id) / "runs").glob("run_*.json"))
            )
            == 4
        )

        documents = _page("1_Documents.py", workspace.workspace_id)
        assert not documents.exception
        assert any("Document ID:" in item.value for item in documents.text)

        run_page = _page("2_Run_Text_Extraction.py", workspace.workspace_id)
        assert not run_page.exception
        assert len(run_page.multiselect[0].value) == 4
        assert run_page.checkbox[0].label == "Re-run (bypass cache)"

        compare = _page("3_Compare.py", workspace.workspace_id)
        if compare.selectbox[-1].value is None:
            compare.selectbox[-1].select(1).run()
        assert not compare.exception
        assert any("RAW" in item.value for item in compare.markdown)
        assert any("cache_hit=" in item.value for item in compare.caption)
    finally:
        manager.end(workspace.workspace_id)
