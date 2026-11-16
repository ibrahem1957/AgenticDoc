# AgenticDoc — Technical Design

**Author:** Claude · **Date:** 2026-11-16 · **Status:** Target architecture for the product **after E5**. Implementation is deferred by the evaluation-first strategy (IMPLEMENTATION_PLAN §0). §5 (document processing) and all model choices are **hypotheses to be validated in the Extraction Lab** ([EXTRACTION_LAB_DESIGN.md](EXTRACTION_LAB_DESIGN.md)). Changes are recorded in §13.
**Inputs:** [REPOSITORY_AUDIT.md](REPOSITORY_AUDIT.md), [MODEL_RESEARCH.md](MODEL_RESEARCH.md), **[SELF_HOSTED_MODEL_SELECTION.md](SELF_HOSTED_MODEL_SELECTION.md) (mandatory, 2026-11-16)**.

---

## 0. Self-hosting requirement (2026-11-16; overrides the OpenRouter-first design in §2, §10, §11)

**Requirement:** the production system must be able to run entirely inside company infrastructure without sending documents to any external AI service. Every model must be downloadable and self-hostable, with a licence that is eligible under SHM §1. Proprietary API-only models are excluded.

### 0.1 Inference gateway with provider adapters
All AI calls go through `src/inference/` (built in E5). No other module talks to a model server directly.

| Role interface | Methods | Backends (adapters) |
|---|---|---|
| `ChatModel` | `chat(messages, …) -> ChatResult` | `openai_compatible` (vLLM, llama.cpp server, SGLang, Ollama; OpenRouter only in the evaluation profile) |
| `VisionModel` | `analyze(image, prompt, schema) -> VisionResult` | `openai_compatible` (vLLM / llama.cpp multimodal) |
| `OCREngine` | `ocr_page(image, hints) -> list[DraftElement]` | `openai_compatible` VLM-OCR (Qari, Nuqta, PaddleOCR-VL, Qwen-VL), `paddleocr` (PP-OCRv5 / PaddleOCR-VL pipeline, in-process or serving), `tesseract` |
| `Embedder` | `embed(texts, kind=query\|document) -> vectors` | `openai_compatible` (vLLM pooling), `tei` (HF Text Embeddings Inference), `sentence_transformers` (in-process, dev) |
| `Reranker` | `rerank(query, docs, top_n)` | `tei`, `vllm_score`, `sentence_transformers` |

- **One HTTP client** for all `openai_compatible` backends, with configurable `base_url`. vLLM, llama.cpp and OpenRouter all expose this API, so the *same* code path runs against a test endpoint or an internal server.
- **Model registry** `config/models.yaml`, with one entry per deployable model: `role`, `backend`, `base_url`, `served_model_name`, `hf_repo`, `hf_revision`, `weights_sha256`, `licence_class` (+ evidence link), `hardware_profile`, `prompt_profile`, optional `openrouter_alias`. **No production default is set until the user approves one** (§0.3). Until then, the app refuses to start a role that has no approved model.
- **Deployment profiles:**
  - `production`: `allow_external_inference=false` is enforced in the client. Every request host must be on `internal_inference_hosts` (allow-list), otherwise it fails before sending. The check also runs at startup. No API keys are required.
  - `evaluation`: hosted **evaluation providers** (OpenRouter, Hugging Face Inference Providers via its OpenAI-compatible router) are allowed only for registry models of Class A/A-tag (Class B with approval) whose `openrouter_alias` / `hf_inference_provider` is set and identity-verified (SHM §1a). Paid calls and real documents need explicit user approval. Each call records `inference_source`, provider and quantization.
- **Reliability:** the timeouts, retries, typed errors and usage ledger from §11 apply to every backend. Usage records tokens, latency and, for local backends, GPU time instead of $ cost.
- **Packaging:** Docker Compose (and optionally Kubernetes manifests) for `app`, `vllm` (one service per model or multi-LoRA), `llama-cpp` (CPU fallback), `tei`, and `paddleocr`. Images and tags are pinned. Weights are mounted read-only from an internal model store. `HF_HUB_OFFLINE=1`; vLLM telemetry disabled (`VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1`); egress blocked except to the inference hosts.

### 0.2 Effects on the rest of this document
- §2: "OpenRouterClient" is replaced by the inference gateway. §10/§11: privacy routing (`provider.data_collection`, `zdr`) applies only to evaluation-profile calls. In production, no data leaves the company network, so third-party retention doesn't arise.
- §5.4 OCR engines: `VLMOCREngine` and `MistralOCREngine` are replaced by the `OCREngine` adapters above. `mistral-ocr` is excluded.
- §5.5 / §7 vision stages: run on a self-hosted VLM. Stage-2 caching is unchanged.
- §6.2 embeddings / §6.5 reranking: self-hosted models only (SHM §2.3/§2.4). bge-m3's native sparse vectors are a candidate for the hybrid retrieval in §6.4.
- §9 agents: the ReAct engine depends only on `ChatModel`. The prompt format must work with the selected open model (tested in the Phase 5 bake-off).

### 0.3 Model approval gate
A model becomes a production default only when: (1) its licence class is A/A-tag, with the licence text confirmed for the pinned revision and legal sign-off recorded; (2) its scores come from an eligible inference source (hosted evaluation provider, local or private GPU, per SHM §1a) on the identical verified Arabic test sets, with a self-hosted serving recipe documented; (3) **the user has personally reviewed the results and approved it**, recorded in `docs/reviews/CLAUDE_REVIEW.md` with the result set IDs.

## 1. Goals and non-goals

**Goals:** multimodal, multi-document, Arabic-first RAG over TXT, native PDFs and scanned PDFs; typed document elements with page-level provenance; grounded answers whose citations are produced by the server, never invented by the model; temporary session storage; preservation of the custom ReAct engine, Tool Registry, Summarizer, Question Generator and Chatbot.

**Non-goals (this project stage):** frontend; user accounts/authentication; permanent storage; DOCX/PPTX/XLSX; handwriting recognition guarantees. (Self-hosted model serving was previously a non-goal. It is now **required**, see §0.)

## 2. Target architecture

```
                    FastAPI (src/api)                    CLI (src/main.py, preserved)
                          │                                       │
                          ▼                                       ▼
                ┌──────────────────── Application services ───────────────────┐
                │ SessionService   IngestionService   ChatService             │
                │ SummaryService   QuestionService                             │
                └───────┬──────────────┬────────────────┬──────────────────────┘
                        │              │                │
         ┌──────────────▼───┐  ┌───────▼────────┐  ┌────▼─────────────────────┐
         │ Sessions         │  │ Ingestion      │  │ Agents (custom ReAct)    │
         │ manager, store,  │  │ validate →     │  │ BaseAgent + ToolRegistry │
         │ TTL sweeper      │  │ classify pages │  │ tools: search_documents, │
         └──────┬───────────┘  │ → extract      │  │ get_section,             │
                │              │ → OCR/vision   │  │ analyze_visual,          │
                │              │ → elements     │  │ list_documents           │
                │              │ → chunk/embed  │  └────┬─────────────────────┘
                │              └───────┬────────┘       │
                ▼                      ▼                ▼
   Session dir (temp FS)      Retrieval: SessionIndex (dense, NumPy) + BM25 (flag)
   originals / page renders   + filters (document_ids) + optional rerank
   / crops / elements.jsonl   Citations: label registry + validator
   / vision cache             Vision: Stage-1 describe, Stage-2 analyze + cache
                                       │
                                       ▼
                        OpenRouterClient (chat, vision, embeddings, rerank)
                        timeouts · retries · typed errors · usage/cost ledger
                        provider privacy flags · redacted logging
```

Framework choice: **FastAPI + Uvicorn**. Justification: no web framework exists today; FastAPI gives multipart upload, Pydantic contracts shared with internal models, OpenAPI docs for the future frontend, and `TestClient` for tests. Ingestion runs in a bounded `ThreadPoolExecutor` (the code is synchronous `requests`; no async rewrite needed). No database, no message queue.

## 3. Package layout (under `Project sdaia/src/`, existing files kept)

```
src/
  config.py                 # pydantic-settings; every model ID / limit / TTL configurable
  main.py                   # CLI (preserved; becomes a thin client of services)
  api/        app.py, routes_sessions.py, routes_documents.py, routes_chat.py, schemas.py, deps.py
  llm/        client.py (OpenRouterClient), errors.py, usage.py, openrouter.py (legacy shim)
  sessions/   manager.py, storage.py, sweeper.py
  documents/  models.py (data contracts), validation.py
  ingestion/  pipeline.py, txt.py, pdf_native.py, page_classifier.py, arabic.py,
              layout.py (headings/header-footer/captions), tables.py, images.py,
              ocr/ (base.py, vlm_ocr.py, mistral_ocr.py)
  vision/     describe.py (Stage 1), analyze.py (Stage 2), cache.py, prompts.py
  rag/        chunker.py (legacy fn kept + structure-aware), embeddings.py, vector_store.py,
              bm25.py, retriever.py, rerank.py, citations.py, normalize.py
  agent/      base.py (refactored ReAct), prompts.py
  tools/      registry.py, file_tool.py (sandboxed), search_tools.py, visual_tools.py
  chatbot/    chat.py
  observability/ observe.py, tracing.py, logging.py
tests/   unit/, integration/, fixtures/
eval/    datasets/, generators/, metrics.py, run_*.py, results/
```

Project root stays `Project sdaia/` (renaming is avoidable churn). `pyproject.toml` goes there; commands run from that directory.

## 4. Data contracts (`src/documents/models.py`, Pydantic v2)

```python
class ElementType(str, Enum):
    TITLE, HEADING, PARAGRAPH, LIST_ITEM, TABLE, IMAGE, CHART, CAPTION,
    HEADER, FOOTER, FOOTNOTE, FORMULA, OTHER

class ExtractionMethod(str, Enum):  NATIVE, OCR_VLM, OCR_MISTRAL, OCR_LOCAL, VLM_DESCRIBE, VLM_ANALYZE
class ExtractionStatus(str, Enum):  OK, PARTIAL, LOW_CONFIDENCE, UNREADABLE, FAILED

class BBox(BaseModel):          # PDF points, origin top-left, page-relative
    x0: float; y0: float; x1: float; y1: float

class TableCell(BaseModel):
    row: int; col: int; text: str; row_span: int = 1; col_span: int = 1
    is_header: bool = False; unreadable: bool = False

class TableData(BaseModel):
    n_rows: int; n_cols: int; cells: list[TableCell]
    markdown: str                      # derived, RTL-safe (no reversed columns)
    direction: Literal["rtl", "ltr"]

class VisualData(BaseModel):
    asset_path: str                    # relative to session dir; never absolute in API output
    image_sha256: str
    kind: Literal["photo", "screenshot", "chart", "diagram", "table_image", "logo", "decorative", "unknown"]
    ocr_text: str | None
    description: str | None            # Stage-1 concise description
    detailed_analysis_ref: str | None  # cache key of Stage-2 full extraction
    analysis_status: Literal["none", "described", "analyzed", "skipped", "failed"]

class Provenance(BaseModel):
    method: ExtractionMethod; model: str | None; prompt_version: str | None
    confidence: float | None           # only when the method provides a real one; never fabricated
    status: ExtractionStatus; warnings: list[str] = []

class DocumentElement(BaseModel):
    element_id: str                    # f"{document_id}:p{page:04d}:e{index:04d}" — stable, unique
    session_id: str; document_id: str; filename: str
    page: int                          # 1-based; TXT uses 1 and line ranges in `offsets`
    page_width: float | None; page_height: float | None
    element_type: ElementType
    reading_order: int                 # global order within the document
    bbox: BBox | None
    section_path: list[str]            # heading ancestry, e.g. ["الفصل الأول", "1.2 المنهجية"]
    parent_id: str | None              # nearest heading element
    related_ids: list[str] = []        # caption ↔ figure/table links
    text: str                          # display text, original characters preserved
    language: Literal["ar", "en", "mixed", "other", "unknown"]
    table: TableData | None = None
    visual: VisualData | None = None
    offsets: tuple[int, int] | None = None   # TXT char offsets
    provenance: Provenance

class DocumentRecord(BaseModel):
    document_id: str; session_id: str; filename: str; original_filename: str
    mime_type: str; size_bytes: int; sha256: str; page_count: int | None
    status: Literal["queued", "extracting", "ocr", "describing", "indexing", "ready", "partial", "failed", "deleted"]
    progress: float; page_kinds: dict[int, str]; counts: dict[str, int]
    warnings: list[str]; error: str | None; created_at: datetime; updated_at: datetime

class Chunk(BaseModel):
    chunk_id: str; session_id: str; document_id: str; filename: str
    element_ids: list[str]; page_start: int; page_end: int
    section_path: list[str]; chunk_type: Literal["text", "table", "visual", "table_row_group"]
    text: str            # evidence text shown to the LLM and quoted
    embed_text: str      # text + context header (see §6.1)
    language: str; token_count: int

class Citation(BaseModel):
    label: str           # "S1" ... assigned by the server per answer
    document_id: str; filename: str; pages: list[int]
    element_ids: list[str]; chunk_id: str; quote: str | None   # verbatim substring of chunk.text if provided

class Answer(BaseModel):
    answer: str; language: str; citations: list[Citation]
    used_visual_analysis: bool; refused: bool; warnings: list[str]
    usage: UsageSummary; trace_id: str
```

`elements.jsonl` per document is the source of truth; chunks and index entries are derived and can be rebuilt.

## 5. Document processing pipeline

### 5.1 Validation (`documents/validation.py`)
- Accept by **magic bytes**, not extension: `%PDF-` → PDF; UTF-8 decodable text (with BOM / UTF-16 detection) → TXT; everything else rejected with HTTP 415.
- Limits (configurable): file ≤ 50 MB, PDF ≤ 500 pages, TXT ≤ 5 MB, ≤ 20 documents per session, ≤ 300 MB per session.
- Open PDFs with a page-count check before full processing; encrypted PDFs → `failed` with a clear error (no password support in scope); malformed PDFs → PyMuPDF exception captured → `failed`, never a 500.
- Filenames: keep `original_filename` (NFC-normalized, control chars stripped, length ≤ 255) for display only; store on disk as `{document_id}.pdf|.txt`. User input never forms a path.

### 5.2 Page classification (`ingestion/page_classifier.py`)
Per page, compute: native character count; ratio of image area to page area; count of `(cid:` / U+FFFD; share of Arabic presentation-form code points (U+FB50–U+FDFF, U+FE70–U+FEFF); share of tokens that are reversed Arabic (heuristic: a sample of words where the reversed string is in a small Arabic lexicon and the original is not — lexicon from the sample corpus, optional).

| Kind | Rule (initial thresholds, tuned in Phase 2 on fixtures) | Strategy |
|---|---|---|
| `native` | ≥ 50 meaningful chars, no garble signals | Native extraction only |
| `scanned` | < 50 chars and an image covers ≥ 60% of the page | Render page → OCR engine |
| `mixed` | Native text + large images containing text | Native text + OCR only of image regions |
| `garbled` | Garble signals above threshold after normalization | Render page → OCR; keep native text as a `warning` comparison only |

### 5.3 Native extraction (`ingestion/pdf_native.py`, `layout.py`)
- PyMuPDF `page.get_text("dict")` → blocks/lines/spans with bbox, font size, flags (bold).
- **Arabic normalization for display text** (`ingestion/arabic.py`): NFKC only on presentation-form code points (to fold shaped glyphs to base letters), remove zero-width artifacts, keep diacritics, keep digits exactly as encoded (Arabic-Indic `٠-٩`, Extended `۰-۹`, Western `0-9`), keep `٫` `٬` `%` `٪` and currency symbols. **No reversal heuristics on text PyMuPDF already ordered**; verify on fixtures.
- Reading order: PyMuPDF block order is the default; for detected multi-column pages, order columns right-to-left when the page's dominant language is Arabic, left-to-right otherwise. Column detection by x-clustering of block centers.
- Headings: font-size z-score relative to the document's body size + bold + short line + numbering patterns (`1.`, `١.`, `الفصل`, `Chapter`, `المبحث`). Produces `section_path` and `parent_id`.
- Headers/footers: text blocks in the top/bottom 8% repeating (normalized, digits masked) on ≥ 50% of pages → `HEADER`/`FOOTER`, excluded from chunks but kept as elements. Page numbers likewise.
- Footnotes: small font in the bottom region beginning with a marker → `FOOTNOTE`.
- Tables: `page.find_tables()`; each table → `TABLE` element with `TableData`; table text is removed from paragraph blocks to avoid duplicate extraction (bbox overlap ≥ 0.5). Columns ordered by the table's direction (RTL if Arabic-dominant header row).
- Images: `page.get_images()` + `get_image_rects()`; skip images < 64×64 px or < 2% of page area (logos/icons → `decorative` unless repeated in the body); dedupe by SHA-256 within a document; save PNG crops to `assets/`.
- Vector charts (drawings without raster images): if a region has a high density of drawing paths and axis-like lines near numeric text, render the region as a crop → `CHART` candidate.
- Captions: a paragraph immediately above/below a figure/table (≤ 30 pt gap) starting with `شكل` / `جدول` / `صورة` / `Figure` / `Fig.` / `Table` / `Chart` → `CAPTION`, linked via `related_ids`.

### 5.4 Scanned / garbled pages (`ingestion/ocr/`)
- Interface: `OCREngine.ocr_page(image: bytes, page_no: int, hints: OCRHints) -> list[DraftElement]`.
- `VLMOCREngine` (default): render at 200 DPI (300 DPI if the first pass reports low confidence or numeric-heavy content), send to the configured OCR model with a strict JSON-schema output: ordered list of elements `{type, text, table?, bbox_hint?}`. Prompt rules: transcribe exactly; preserve diacritics and digit forms; never complete or correct words; mark unreadable spans with `⟦?⟧`; tables as cell grids; no translation.
- `MistralOCREngine` (optional): OpenRouter file-parser `mistral-ocr`; maps Markdown back to page elements (no bboxes).
- OCR elements get `provenance.method = OCR_VLM`, `bbox = None` unless the model's region hint is validated, and `status = LOW_CONFIDENCE` when `⟦?⟧` occurs.
- Validation: output must parse; if the element texts are empty but the page has visible content (image variance), retry once at higher DPI; then `UNREADABLE`.

### 5.5 Stage 1 visual processing at ingestion (`vision/describe.py`)
- Only for significant images (after size filter and dedupe), detected chart regions, and table images in native pages.
- **One** call per visual (batched up to 4 images per request when the model supports it): returns `{kind, ocr_text, description (≤ 80 words, document language), key_values_visible: [...], has_numeric_data: bool}`.
- `key_values_visible` contains only values **printed** in the image. If `has_numeric_data` is true and values are not printed (e.g., bars without labels), Stage 1 records that and does not estimate.
- Result stored on the element; status `described`.
- Budget: `max_visual_calls_per_document` (default 60); excess visuals → `skipped` with a warning; they remain analyzable in Stage 2.

### 5.6 Avoiding duplicates and contradictions
- Native text inside a table bbox is attributed to the table only.
- Image OCR text in `mixed` pages is attached to the image element, not emitted as separate paragraphs, unless the image covers ≥ 60% of the page (then it is a scanned region and its OCR elements replace the image).
- When both native text and OCR exist for a `garbled` page, only OCR text is indexed; native text is retained in `provenance.warnings` for audit.

## 6. Multi-document RAG

### 6.1 Structure-aware chunking (`rag/chunker.py`)
- Chunks never cross document boundaries; they do not cross section boundaries unless a section is smaller than `min_chunk_tokens` (merge with the next sibling inside the same parent).
- Target 350–500 tokens (tokenizer: `tiktoken` `cl100k_base` as a consistent approximation), split at paragraph → sentence (Arabic `.؟!؛` and Latin punctuation) → word boundaries; overlap = one sentence.
- Tables: small tables (≤ 400 tokens) → one `table` chunk with caption + Markdown. Large tables → `table_row_group` chunks of N rows, each **repeating the header row** and the caption.
- Visuals: one `visual` chunk per described visual: caption + description + ocr_text + printed key values.
- `embed_text` = `"Document: {filename} | Section: {' > '.join(section_path)} | Page: {page}\n{text}"`. The header improves scoped retrieval; `text` (without header) is what the LLM sees and quotes.
- The legacy `chunk_text()` function stays for backward compatibility of the CLI until Phase 5 switches the CLI to the new pipeline.

### 6.2 Embeddings (`rag/embeddings.py`)
- Batched requests (≤ 64 inputs or ≤ 100k tokens per call), retries via the client, one model per session index (stored in index metadata; mixing models in one index is rejected).
- Query-side instruction for instruction-aware models (Qwen3-Embedding): `"Instruct: Given a question, retrieve passages from documents that answer it\nQuery: {q}"`, configured per model in `config.py`.
- L2-normalize at insertion; zero vectors rejected.

### 6.3 Session index (`rag/vector_store.py`)
- `SessionIndex` holds a contiguous `float32` matrix + parallel arrays of `chunk_id`, `document_id`; `search(query_vec, k, document_ids: set | None)` uses a boolean mask then `argpartition` (vectorized).
- `remove_document(document_id)` compacts the matrix. Adding documents appends. A per-session `threading.RLock` guards mutation.
- Kept in memory and **also** saved as `index.npz` + `chunks.jsonl` in the session dir, so a document deletion is verifiable on disk and so ingestion workers can hand off safely. Not reloaded across process restarts (see §8).

### 6.4 Sparse retrieval (`rag/bm25.py`, behind `RETRIEVAL_HYBRID=true`)
- `rank_bm25`-style BM25 over a search-normalized form: remove diacritics and tatweel, unify `أ إ آ ٱ → ا`, `ى → ي`, `ة → ه` (search form only), map Arabic-Indic digits to Western **in the search form only**, lowercase Latin.
- Fusion: Reciprocal Rank Fusion (k = 60) of dense top-50 and BM25 top-50.
- Enabled by default only if the Phase 4 evaluation shows a gain; otherwise it remains optional.

### 6.5 Reranking (`rag/rerank.py`, behind `RERANK_ENABLED=false`)
OpenRouter `/api/v1/rerank` over the fused top-30 → top-8. Gate: see MODEL_RESEARCH §6.

### 6.6 Scope and contamination control
- Every query requires a resolved scope: `document_ids` (explicit list) or `"all"` (= all `ready`/`partial` documents in this session at query time). Unknown or foreign document IDs → HTTP 404 (never silently ignored).
- Retrieval filters by mask **before** ranking. Every retrieved chunk carries `document_id`; a post-condition assertion rejects any chunk outside scope (defense in depth; tested).
- The index object is reachable only through its session; there is no global store.

### 6.7 Cross-document questions and comparison
- `ChatService` detects comparison intent (cheap heuristics: "قارن", "الفرق", "compare", "difference", "vs", or ≥ 2 documents explicitly named) and switches to **per-document retrieval**: top-k per document in scope (k = 4) instead of global top-k, so one document cannot crowd out others.
- The context block is grouped by document. The prompt instructs: report each document's value with its citation; when values differ, state the difference explicitly with both sources; never reconcile or average.

### 6.8 Citations (`rag/citations.py`) — the core grounding mechanism
1. The server builds the context with server-assigned labels: `[S1] (Document: report.pdf, p. 4, Section: النتائج)\n<chunk text>`.
2. The model must cite with `[S#]` only.
3. After generation, the validator parses all `[S#]`: labels not in the label registry are **removed** and a warning is added; the answer is flagged if a factual sentence has no citation (heuristic, warning only).
4. `Citation` objects (document, pages, element_ids) are derived from the registry — the model never produces filenames or page numbers. Filenames/pages inside the answer text that do not match cited sources trigger a warning.
5. Optional `quote`: if the model provides a quote, it is kept only if it is a verbatim (normalized-whitespace) substring of the chunk text.

## 7. Two-stage visual understanding

### Stage 1 (ingestion) — §5.5.

### Stage 2 (question time) (`vision/analyze.py`)
```
retrieve → evidence includes CHART/IMAGE/TABLE elements?
         → sufficiency check (deterministic rules first):
             needs_visual = question asks for values/trends/comparison/reading of a figure
                            (keyword + numeric-intent patterns, AR/EN)
                            AND the retrieved visual element lacks those values in
                            printed key_values / table cells / ocr_text
           if ambiguous → the ReAct chat agent may call tool analyze_visual(element_id)
         → analyze_visual: cache lookup → else VLM call on the original crop
           (or page render if crop missing) with a full-extraction prompt
         → validated result added as evidence chunk with its own [S#] label
```
- **Full extraction, not question-specific**: Stage 2 asks for a complete structured reading (title, axes, units, legend, series, each data point with `{label, value, value_source: "printed" | "estimated_from_axis", unreadable: bool}`). One cached result serves all future questions about that visual.
- **Number safety:** values with `value_source = "estimated_from_axis"` may only be presented as approximate ("≈", "تقريبًا") and are labeled in the answer; `unreadable` values are never filled in. The answer prompt states this rule, and a post-check verifies that numbers in the answer that originate from a chart evidence block appear in that block.
- **Cache (`vision/cache.py`)**: session-scoped, key = `sha256(image_bytes) + model + prompt_version`; stored in memory and as JSON under `sessions/{sid}/vision_cache/`. Concurrent requests for the same key are coalesced (per-key lock). Deleted with the document (index of keys per `document_id`) and with the session.
- Limits: ≤ 2 Stage-2 analyses per question (configurable), Stage-2 model configurable separately from Stage 1.

## 8. Session lifecycle

| Aspect | Definition |
|---|---|
| Creation | `POST /sessions` → `session_id = secrets.token_urlsafe(24)` (unguessable; acts as a capability because there is no auth). |
| Storage root | `AGENTICDOC_TMP_DIR` (default `tempfile.gettempdir()/agenticdoc`), permissions `0o700` where the OS supports it. |
| Layout | `sessions/{sid}/session.json`, `documents/{did}/original.{ext}`, `documents/{did}/elements.jsonl`, `documents/{did}/assets/*.png`, `documents/{did}/pages/*.png`, `index.npz`, `chunks.jsonl`, `vision_cache/*.json` |
| Idle expiry | Session expires `SESSION_IDLE_TTL` (default 60 min) after the last API call that references it. |
| Absolute expiry | `SESSION_MAX_TTL` (default 24 h) after creation, regardless of activity. |
| Sweeper | Background thread every 5 min: expire sessions, cancel their ingestion jobs, delete dirs. |
| Expired access | HTTP 410 Gone for known-recently-expired IDs (kept in a small tombstone set for 1 h), else 404. |
| Document deletion | Mark `deleted` → cancel in-flight ingestion (cooperative cancellation token checked between pages) → remove chunks from index + BM25 → remove vision cache entries → delete `documents/{did}/` → persist index. Idempotent. |
| Session deletion | Cancel all jobs → drop in-memory state → `shutil.rmtree` session dir. Idempotent. |
| Restart / crash | Sessions **do not survive a restart**. On startup the app deletes every directory under `sessions/` (they are orphans by definition). Documented in API docs. |
| Concurrency | Per-session `RLock` for mutations; ingestion jobs per session limited (default 2 concurrent documents). |
| No permanent storage | No DB. Nothing outside the session dir except logs, which contain no document content. |

**Third-party retention (separate from local deletion):** content sent to OpenRouter and upstream providers is governed by their policies (MODEL_RESEARCH §10). Local deletion cannot recall it. Requests are sent with `provider.data_collection = "deny"`; optional `zdr = true`.

## 9. Agents and chatbot

### 9.1 `BaseAgent` refactor (preserve the concept, fix D6–D8)
- `run(task, context)` creates a fresh `AgentRunState` (scratchpad, seen hashes, budgets) **per run**.
- The prompt contains: system prompt, task, tool descriptions (from the registry), and the **full scratchpad** of prior steps (truncated from the oldest observation, by token budget).
- Action format stays text-based ReAct (`THOUGHT:` / `ACTION:` / `INPUT:` JSON / `FINAL:`), parsed case-insensitively; invalid format → one corrective observation, then fail cleanly.
- Budgets: `max_steps` (default 6), `max_llm_calls`, `max_tool_calls`, wall-time; exceeded → structured `stopped_reason`.
- Each step emits a trace event (§11). LLM errors raise typed exceptions; the agent returns `status="error"` instead of treating error text as output.

### 9.2 Tool registry
`ToolRegistry.register(name, fn, description, input_schema, session_scoped=True)`. Session tools receive a `ToolContext(session_id, scope, trace)` injected by the agent — **the model never chooses the session or arbitrary paths**. Tools: `search_documents(query, document_ids?)`, `get_section(document_id, section_path)`, `analyze_visual(element_id)`, `list_documents()`. `read_file` is removed from the agent-exposed registry; kept only for the legacy CLI path, confined to an allow-listed directory via `Path.resolve()` + `is_relative_to`.

### 9.3 Chatbot
- Default path is a **single retrieval + single generation call** (cheap). The ReAct path (with `analyze_visual`, follow-up searches) is used only when the sufficiency check says evidence is insufficient or for comparison questions. Max LLM calls per question: 4.
- Follow-ups: per-session conversation memory (last 6 turns); the question is rewritten into a standalone query only when it contains anaphora/short follow-up patterns (one cheap LLM call) — otherwise used as-is.
- Language: detect question language (Arabic script ratio); answer in that language; quoted evidence stays in the source language.
- Refusal: if no retrieved chunk passes a minimum score and the model indicates no support → fixed refusal message in the user's language, `refused=true`, no citations.

### 9.4 Summarizer (fix D2)
Map-reduce over **all** sections of the selected document(s): section summaries (with their `[S#]` labels kept) → document summary → optional cross-document synthesis. Token-budgeted; long documents processed in batches. Output carries citations to sections/pages.

### 9.5 Question generator (fix D3)
Samples evidence chunks stratified across sections (and documents), generates questions **with the answer and its `[S#]` source**, validates that each cited label exists, and deduplicates by normalized text. Supports `language`, `count`, `difficulty`.

## 10. API (FastAPI)

| Method & path | Purpose | Response |
|---|---|---|
| `POST /sessions` | Create session | `201 {session_id, expires_at, limits}` |
| `GET /sessions/{sid}` | Session info | `{documents: n, expires_at, usage}` |
| `DELETE /sessions/{sid}` | End session | `204` |
| `POST /sessions/{sid}/documents` | Upload (multipart, 1 file per request) | `202 {document_id, status: "queued"}` |
| `GET /sessions/{sid}/documents` | List | `[DocumentRecord]` |
| `GET /sessions/{sid}/documents/{did}` | Status / extraction report | `DocumentRecord` |
| `GET /sessions/{sid}/documents/{did}/elements?page=&type=` | Inspect extraction (dev) | paged `[DocumentElement]` |
| `DELETE /sessions/{sid}/documents/{did}` | Remove document + derived data | `204` |
| `POST /sessions/{sid}/chat` | `{question, document_ids: [..] or "all"}` | `Answer` |
| `POST /sessions/{sid}/summaries` | `{document_ids, mode: "per_document" or "combined", language?}` | `{summaries, citations, usage}` |
| `POST /sessions/{sid}/questions` | `{document_ids, count, difficulty, language?}` | `{questions: [{question, answer, citations}]}` |
| `GET /health` | Liveness | `{status}` |

Errors use one envelope: `{error: {code, message, details?}}`. Codes: `invalid_file`, `file_too_large`, `session_not_found`, `session_expired`, `document_not_found`, `document_not_ready`, `upstream_error`, `upstream_rate_limited`, `budget_exceeded`.

CLI (`python -m src.main <file> [<file>...]`) uses the same services in-process.

## 11. Reliability, observability, cost

- **Inference client** (§0.1; formerly "OpenRouterClient", superseded 2026-11-16): `requests.Session`; connect timeout 10 s, read timeout 120 s (vision 180 s); retries with exponential backoff + jitter on 429/5xx/timeouts (max 4, honoring `Retry-After`); no retry on 400/401/402/403; typed errors (`AuthError`, `RateLimitError`, `UpstreamError`, `InvalidResponseError`, `ContentTooLargeError`); response schema validation; `HTTP-Referer`/`X-Title` headers; `provider` privacy object on every request.
- **Usage ledger**: every call records `{trace_id, session_id, operation, model, prompt_tokens, completion_tokens, image_count, cost_usd (from response usage if provided, else estimated from catalog price table), latency_ms, status}`; aggregated per session and returned in API responses. Per-session budget `SESSION_MAX_COST_USD` (default $1.00) → `budget_exceeded`.
- **Tracing**: structured JSON log events (`agent.step`, `tool.call`, `llm.call`, `ingest.page`, `vision.cache_hit`). Content-free at INFO (lengths, hashes, IDs only). `DEBUG_CONTENT_LOGGING=true` enables content in logs for local development only; refuses to start with it when `ENV=production`.
- **Redaction**: API key never logged; exceptions logged with type + status code, not request bodies.

## 12. Security

| Threat | Control |
|---|---|
| API key exposure | Env / `.env` only; `.env` in `.gitignore`; `.env.example` committed; key redacted in logs and errors |
| Malicious uploads | Magic-byte validation, size/page limits, PyMuPDF in try/except, per-page timeout, image decompression limit (max pixels), no external resources fetched |
| Path traversal | Server-generated file names; all paths built from IDs under the session root and verified with `is_relative_to` |
| Session isolation | Unguessable IDs; per-session state objects; no global index; tests for cross-session access |
| Prompt injection from documents | Document text placed only inside delimited `<evidence>` blocks with an explicit instruction that evidence is data, not instructions; agents have no tools with side effects outside the session; no filesystem/network tools; citations server-generated; output never executed |
| Upstream errors / rate limits | Typed errors, retries, budget limits, clear API error codes |
| Cost runaway | Per-document visual budget, per-question call limits, per-session cost cap |

## 13. Design change log
| Date | Change | Reason |
|---|---|---|
| 2026-11-16 | Initial design | — |
| 2026-11-16 | Implementation deferred; §5 and model choices become Lab hypotheses (E1–E4), finalized in E5 | User requested evaluation-first strategy |
| 2026-11-16 | **Clarification:** OpenRouter and HF Inference Providers are restored as *evaluation providers* for eligible open-weight models, and hosted results count in rankings. Production stays fully self-hosted. API-only models stay excluded | User clarification; SHM §1a |
| 2026-11-16 | **Self-hosting requirement:** new §0 (inference gateway, provider adapters, model registry, production egress enforcement, approval gate); OpenRouter demoted to an evaluation-only test endpoint for eligible open-weight models; proprietary API models excluded | User requirement; SELF_HOSTED_MODEL_SELECTION.md |
| 2026-11-16 | §5.2/§5.3 caveat: "native" pages are not exact by default. The page classifier must use E1-measured signals (presentation forms, ligatures, digit forms, reversal), and the "no reversal heuristics" rule in §5.3 is re-decided in E5 from E1 data | Feasibility probe, EXTRACTION_LAB_DESIGN §7 |
