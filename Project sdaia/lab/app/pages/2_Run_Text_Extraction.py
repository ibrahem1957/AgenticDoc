from __future__ import annotations

import streamlit as st

from lab.core.adapters.registry import AdapterRegistry
from lab.core.ingest import IngestService
from lab.core.runner import LabRunner
from lab.core.settings import load_settings
from lab.core.workspace import WorkspaceManager


st.set_page_config(page_title="Run extraction — Extraction Lab", layout="wide")
settings = load_settings()
manager = WorkspaceManager(settings)
if "workspace_id" not in st.session_state:
    st.warning("Create a workspace on Home first.")
    st.stop()
workspace_id = st.session_state.workspace_id
ingest = IngestService(manager, settings)
registry = AdapterRegistry()
runner = LabRunner(manager, settings, registry)

st.title("Run Text Extraction")
documents = ingest.list_documents(workspace_id)
if not documents:
    st.info("Upload a document first.")
    st.stop()

by_label = {f"{item.display_name} ({item.doc_id})": item for item in documents}
document = by_label[st.selectbox("Document", list(by_label))]
pages_text = st.text_input("Pages (comma-separated)", value="1")
try:
    pages = sorted(
        {int(value.strip()) for value in pages_text.split(",") if value.strip()}
    )
    if not pages or pages[0] < 1 or pages[-1] > document.page_count:
        raise ValueError
except ValueError:
    st.error("Enter valid 1-based page numbers within this document.")
    st.stop()

entries = registry.list("text")
available_local = [
    entry for entry in entries if entry.info.kind == "local" and entry.info.available
]
labels = {entry.info.label: entry.info.adapter_id for entry in available_local}
selected_labels = st.multiselect("Local extractors", list(labels), default=list(labels))
repeat = st.selectbox("Repeat (timing)", [1, 3], index=0)
bypass_cache = st.checkbox(
    "Re-run (bypass cache)",
    help="Execute the selected extractors again even when a successful cached result exists.",
)

if st.button("Run local extraction", type="primary"):
    progress = st.progress(0)
    results = []
    for index, label in enumerate(selected_labels, start=1):
        result = runner.run_local(
            workspace_id,
            document,
            ingest.original_path(workspace_id, document.doc_id),
            labels[label],
            pages,
            repeats=int(repeat),
            bypass_cache=bypass_cache,
        )
        results.append(result)
        WorkspaceManager.atomic_write_json(
            manager.path(workspace_id) / "runs" / f"{result.run_id}.json",
            result.model_dump(mode="json"),
        )
        progress.progress(index / max(1, len(selected_labels)))
        st.text(
            f"{label}: {result.status} — extraction {result.wall_ms:.2f} ms; "
            f"startup {result.startup_ms:.2f} ms; overlay {result.overlay_ms:.2f} ms; "
            f"cache_hit={result.cache_hit}"
        )
    st.session_state.latest_run_ids = [item.run_id for item in results]
    st.session_state.latest_doc_id = document.doc_id
    st.success("Runs saved. Open Compare to inspect raw text beside the original page.")
