from __future__ import annotations

import json

import streamlit as st

from lab.app.components import overlay_blocks, runs_for_page_set, text_html
from lab.core.ingest import IngestService
from lab.core.models import RunResult
from lab.core.settings import load_settings
from lab.core.workspace import WorkspaceManager


st.set_page_config(page_title="Compare — Extraction Lab", layout="wide")
settings = load_settings()
manager = WorkspaceManager(settings)
if "workspace_id" not in st.session_state:
    st.warning("Create a workspace on Home first.")
    st.stop()
workspace_id = st.session_state.workspace_id
ingest = IngestService(manager, settings)

st.title("Compare RAW extraction")
run_files = sorted((manager.path(workspace_id) / "runs").glob("run_*.json"))
runs = [
    RunResult.model_validate_json(path.read_text(encoding="utf-8"))
    for path in run_files
]
if not runs:
    st.info("Run text extraction first.")
    st.stop()

doc_ids = sorted({run.doc_id for run in runs})
doc_id = st.selectbox(
    "Document",
    doc_ids,
    index=doc_ids.index(st.session_state.get("latest_doc_id", doc_ids[0]))
    if st.session_state.get("latest_doc_id") in doc_ids
    else 0,
)
document = ingest.get(workspace_id, doc_id)
doc_runs = [run for run in runs if run.doc_id == doc_id]
page_sets = sorted({tuple(page.page for page in run.pages) for run in doc_runs})
selected_page_set = st.selectbox(
    "Run page set",
    page_sets,
    format_func=lambda value: ", ".join(str(page) for page in value),
)
if selected_page_set is None:
    st.info("Select a run page set to compare.")
    st.stop()
show_all_runs = st.checkbox("Show all runs, including older duplicates")
doc_runs = runs_for_page_set(doc_runs, selected_page_set, show_all=show_all_runs)
pages = list(selected_page_set)
page_number = st.selectbox("Page", pages)
if page_number is None:
    st.info("Select a page to compare.")
    st.stop()
show_overlay = st.checkbox("Show block-order overlay", value=True)
monospace = st.checkbox("Monospace text")
show_invisibles = st.checkbox("Show invisible and presentation-form markers")

image_path = ingest.render_page(workspace_id, doc_id, page_number)
columns = st.columns([1.15] + [1 for _ in doc_runs])
columns[0].subheader("Original page")
columns[0].image(image_path, width="stretch")

for column, run in zip(columns[1:], doc_runs, strict=False):
    column.subheader(run.adapter.label)
    column.caption(
        f"Params: {json.dumps(run.adapter.params, ensure_ascii=False, sort_keys=True)} · "
        f"extraction: {run.wall_ms:.2f} ms · startup: {run.startup_ms:.2f} ms · "
        f"overlay: {run.overlay_ms:.2f} ms · cache_hit={run.cache_hit}"
    )
    page_result = next((item for item in run.pages if item.page == page_number), None)
    if page_result is None:
        column.warning("No result for this page")
        continue
    if show_overlay and page_result.blocks:
        column.image(
            overlay_blocks(image_path, document, run, page_number),
            caption="Numbered extraction blocks",
            width="stretch",
        )
    column.markdown("**RAW — exactly as extracted**")
    column.markdown(
        text_html(
            page_result.text, monospace=monospace, show_invisibles=show_invisibles
        ),
        unsafe_allow_html=True,
    )
    column.caption(
        f"Status: {page_result.status}; {page_result.elapsed_ms or 0:.2f} ms"
    )

st.warning(
    "E1-A is not complete from automated tests alone. Upload a PDF manually and verify that the rendered page, Arabic display, raw text, and extractor comparison are correct on this Windows machine."
)
