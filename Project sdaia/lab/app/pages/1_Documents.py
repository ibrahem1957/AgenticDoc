from __future__ import annotations

import streamlit as st

from lab.app.components import document_metadata_text
from lab.core.ingest import IngestError, IngestService
from lab.core.settings import load_settings
from lab.core.workspace import WorkspaceManager


st.set_page_config(page_title="Documents — Extraction Lab", layout="wide")
settings = load_settings()
manager = WorkspaceManager(settings)
if "workspace_id" not in st.session_state:
    st.warning("Create a workspace on Home first.")
    st.stop()
service = IngestService(manager, settings)
workspace_id = st.session_state.workspace_id

st.title("Documents")
uploads = st.file_uploader(
    "Upload PDFs or images",
    type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "webp"],
    accept_multiple_files=True,
)
if uploads and st.button("Add to temporary workspace", type="primary"):
    for upload in uploads:
        try:
            service.ingest(workspace_id, upload, upload.name)
            st.success(f"Added {upload.name}")
        except IngestError as exc:
            st.error(f"{upload.name}: {exc}")

documents = service.list_documents(workspace_id)
if not documents:
    st.info("No documents uploaded yet.")
    st.stop()

for document in documents:
    with st.expander(
        f"{document.display_name} — {document.page_count} page(s)", expanded=True
    ):
        st.text(document_metadata_text(document))
        page = st.number_input(
            "Page to preview",
            min_value=1,
            max_value=document.page_count,
            value=1,
            key=f"page_{document.doc_id}",
        )
        try:
            st.image(
                service.render_page(workspace_id, document.doc_id, int(page)),
                caption=f"Original page {page}",
            )
        except IngestError as exc:
            st.error(str(exc))
        if st.button("Delete document", key=f"delete_{document.doc_id}"):
            service.delete(workspace_id, document.doc_id)
            st.rerun()
