# AgenticDoc — Phased Implementation Plan

**Planner/Reviewer:** Claude · **Implementer:** Codex · **Date:** 2026-11-16 (revised 2026-11-16: evaluation-first strategy)
References: [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) (TD), [EXTRACTION_LAB_DESIGN.md](EXTRACTION_LAB_DESIGN.md) (LAB), [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) (AC), [REPOSITORY_AUDIT.md](REPOSITORY_AUDIT.md) (defects D1–D20).

## 0. Strategy change (2026-11-16) — evaluation first

The user wants to test extraction tools and models on their own documents before the production pipeline is chosen. The execution order is now:

| Phase | Name | Status | Gate |
|---|---|---|---|
| **E1** | **Extraction Lab + text extraction evaluation** (native PDF text layers), in checkpoints E1-A → E1-D, each independently reviewed | **Issued 2026-11-16 — E1-A first** | AC-E1 (all 21 items) |
| E2 | Arabic OCR model comparison (VLMs via OpenRouter, `mistral-ocr`, optional local NAMAA Qari-OCR / PaddleOCR-VL) | Planned | AC-E2 (defined at E2 kickoff) |
| E3 | Table extraction evaluation | Planned | AC-E3 |
| E4 | Chart understanding evaluation | Planned | AC-E4 |
| E5 | Select and integrate the validated extraction pipeline into AgenticDoc | Planned; absorbs Phases 1–2 below | AC-E5 |
| 3–6 | Multimodal, multi-document RAG, agents, hardening (below) | **Deferred until after E5** | AC-3 … AC-6 |

Consequences:
- **The former Phase 1 task ("Backend foundation") is withdrawn before implementation.** It is archived at `docs/handoff/archive/CODEX_TASK_phase1_foundation_SUPERSEDED.md`. Its content (OpenRouter client hardening, config, sessions, FastAPI) is reused in E5. The Lab's own small client and workspace code serve as prototypes for it.
- **No refactoring of `src/` during E1–E4.** The existing CLI must keep working unchanged.
- TD §5 (document processing) and the model choices in MODEL_RESEARCH §9 are now **hypotheses to be tested in the Lab**, not decisions. E5 updates them with measured evidence.
- The Phase 1–6 sections below stay as the post-E5 roadmap. They will be revised at E5 with the measured results.

### E1 — Extraction Lab + text extraction (summary; the task is in `docs/handoff/CODEX_TASK.md`)
- **Objective:** a local Streamlit lab where the user uploads PDFs/images, runs several text-layer extractors on the same pages, inspects them next to the page image, edits and verifies ground truth, and sees CER/WER (verified ground truth only), diagnostics, human-review records, timing and cost, then exports reports.
- **Existing modules affected:** none. A new package `Project sdaia/lab/` and `Project sdaia/tests/lab/`; root `.gitignore` additions.
- **Adapters:** PyMuPDF, pypdfium2, pdfplumber, pypdf (local), and OpenRouter file-parser (`cloudflare-ai`, `mistral-ocr`) behind explicit confirmation.
- **Out of scope:** OCR/VLM adapters, tables, charts, any change to `src/`, a production frontend, RAG.
- **Risks:** synthetic fixtures produced by PyMuPDF may favour PyMuPDF's extractor (mitigation: real user documents, and fixtures from a second producer where possible, see LAB §7); Streamlit statefulness bugs (mitigation: all logic in `lab.core`, tested without Streamlit).

### E2–E4 (outline; detailed tasks issued after the previous phase is approved)
- **E2:** add the `ocr` task: page-image renders at configurable DPI and degradation variants; VLM adapters with model IDs from config validated against `/api/v1/models` (shortlist in MODEL_RESEARCH §4); `mistral-ocr`; optional local adapters (Qari-OCR 0.4, PaddleOCR-VL) that disable themselves without their dependencies or a GPU; scanned fixtures produced by rasterizing E1 fixtures; the user's scanned documents.
- **E3:** add the `table` task: cell-grid ground-truth editor, cell EM / numeric cell EM / TEDS; adapters PyMuPDF `find_tables`, pdfplumber, best E2 VLMs, optionally Docling.
- **E4:** add the `chart` task: data-point ground truth with `printed`/`estimated` flags; printed-value EM, abstention rate, hallucinated-value rate; VLM adapters.
- **E5:** write `MODEL_EVAL_RESULTS.md` from the Lab exports, update TD §5 and MODEL_RESEARCH §9 with measured choices, then implement the foundation (former Phase 1) and the validated extraction (former Phase 2/3 extraction parts) in `src/`.

## Ground rules for every phase
1. Work on a branch `phase-N-<slug>` from the latest approved `main`; one PR per phase (corrections go on the same branch).
2. Do not change interfaces defined in TD without a written proposal in `CODEX_REPORT.md` → "Design deviations", approved by Claude.
3. All model IDs, limits, TTLs from `src/config.py`. No hard-coded model strings outside config defaults.
4. Unit tests never call the network: use the fake OpenRouter transport (Phase 1). Live tests are marked `@pytest.mark.live` and skipped without `OPENROUTER_API_KEY`.
5. No document content in logs at INFO level.
6. The legacy CLI (`python -m src.main`) must keep working at the end of every phase.
7. Deliver `docs/handoff/CODEX_REPORT.md` with the exact commands run and their verbatim output summary.

## Phase overview

| Phase | Name | Depends on | Gate |
|---|---|---|---|
| 1 | Backend foundation | — | AC-1 |
| 2 | Structured deterministic extraction (TXT, native PDF) | 1 | AC-2 |
| 3 | Multimodal: OCR, Stage-1/Stage-2 vision, caching (+ OCR/vision bake-off) | 2 | AC-3 |
| 4 | Multi-document RAG: chunking, embeddings, retrieval, citations (+ embedding/rerank bake-off) | 2 (3 for visual chunks) | AC-4 |
| 5 | Agent integration: ReAct refactor, chat, summarizer, questions, API completion | 4 | AC-5 |
| 6 | Testing & hardening: full evaluation, security, large docs, cleanup | 5 | AC-6 |

Phases 3 and 4 may run in parallel after Phase 2 if two branches are coordinated; visual chunks (Phase 4) consume Phase 3's elements through the contract only.

### Audit defect → fixing phase
| Defect (REPOSITORY_AUDIT §4) | Fixed in |
|---|---|
| D10, D11, D17 (HTTP timeouts/retries/status/key checks), D20 (packaging/hygiene) | Phase 1 |
| D14 (content in logs) | Phase 1 for new code; legacy `print`s removed in Phase 5 |
| D5 (errors as answers) | Phase 1 client raises typed errors; legacy string behavior removed in Phase 5 |
| D12 (no metadata), D13 (character chunking), D16 (zero vector) | Phase 2 (elements) + Phase 4 (chunks/index) |
| D1 (impossible citations), D9 (duplicate indexing) | Phase 4 (citations) + Phase 5 (single shared session index) |
| D2, D3 (summary/questions coverage), D4 (unsafe `read_file`), D6–D8 (ReAct state), D15 (single-turn), D18, D19 | Phase 5 |

---

## Phase 1 — Backend foundation

**Objective:** A runnable, testable backend skeleton with config, hardened OpenRouter client, data contracts, session lifecycle, upload/list/delete endpoints (storage only), observability primitives, and evaluation-harness scaffolding — without changing the behavior of existing agents.

**Existing modules affected:** `llm/openrouter.py` (becomes a shim over the new client, same public `invoke()` signature), `rag/embeddings.py` (uses the new client, adds batching; same public `embed()`), `observability/observe.py` (kept), `main.py` (load config; otherwise unchanged).

**New modules:** `config.py`, `llm/client.py`, `llm/errors.py`, `llm/usage.py`, `documents/models.py`, `documents/validation.py`, `sessions/{manager,storage,sweeper}.py`, `api/{app,deps,schemas,routes_sessions,routes_documents}.py`, `observability/{logging,tracing}.py`, `tests/…`, `eval/metrics.py`, `eval/run_ocr_bakeoff.py` (skeleton), `pyproject.toml`, `requirements*.txt`, `.gitignore`, `.env.example`.

**Tasks:** see `docs/handoff/CODEX_TASK.md` (authoritative for Phase 1).

**Interfaces:** TD §4 (all models defined now, even if populated later), TD §8, TD §10 (session + document routes only), TD §11.

**Dependencies:** `fastapi`, `uvicorn`, `pydantic>=2`, `pydantic-settings`, `python-multipart`, `requests`, `numpy`, `python-dotenv`, `tiktoken`; dev: `pytest`, `pytest-cov`, `httpx` (TestClient), `ruff`. PyMuPDF is **not** needed until Phase 2 (except page counting for validation — allowed in Phase 1 if needed; see task).

**Testing:** unit tests for config, client (fake transport: success, 429 with Retry-After, 500 retry then success, 401 no retry, timeout, malformed JSON), usage ledger, validation (magic bytes, size, filename sanitization), session lifecycle (create, idle expiry, max expiry, delete, sweeper, startup cleanup), API routes with TestClient; metrics unit tests (CER/WER known values).

**Acceptance:** AC-1.

**Risks:** over-building the API before extraction exists (mitigation: routes limited to sessions/documents storage); OpenRouter usage/cost fields differ from assumptions (mitigation: parse defensively, fall back to catalog-price estimate, record which source was used).

**Out of scope:** PDF extraction, OCR, vision calls, chunking changes, retrieval changes, agent changes, chat/summary/question endpoints.

---

## Phase 2 — Structured deterministic extraction

**Objective:** Convert TXT and native PDFs into `DocumentElement` streams with page/bbox/section provenance; classify pages; produce page renders and image crops for Phase 3. Zero model calls.

**Existing modules affected:** none functionally (CLI keeps the legacy path).

**New modules:** `ingestion/{pipeline,txt,pdf_native,page_classifier,arabic,layout,tables,images}.py`, `eval/generators/synthetic_pdfs.py`, `tests/fixtures/…`.

**Tasks:**
1. `ingestion/arabic.py`: presentation-form folding, zero-width cleanup, language detection (script ratios), digit-preserving normalization; `search_normalize()` (for Phase 4 BM25) kept separate from display normalization.
2. `txt.py`: encoding detection (UTF-8/UTF-8-BOM/UTF-16), paragraph splitting, heading heuristics (Markdown `#`, numbered headings in Arabic/Western digits, short standalone lines), offsets.
3. `pdf_native.py` + `layout.py`: spans/blocks with bbox, multi-column ordering (RTL-aware), heading detection with section tree, header/footer/page-number detection, footnotes, captions + linking.
4. `tables.py`: `find_tables()`, cell grid, RTL column order, header detection, Markdown rendering; remove table text from paragraphs.
5. `images.py`: image extraction, size/area filters, SHA-256 dedupe, crop PNGs, vector-chart region candidates.
6. `page_classifier.py`: TD §5.2 signals and kinds; thresholds in config.
7. `pipeline.py`: orchestrate per document; write `elements.jsonl`; update `DocumentRecord` status/progress/counts/warnings; cooperative cancellation; wire into the upload route (status goes to `ready` for native docs; `scanned`/`garbled` pages flagged `pending_ocr` for Phase 3).
8. Synthetic fixture generator (PyMuPDF `insert_htmlbox` with `dir="rtl"` HTML and an embedded Arabic font, e.g. Noto Naskh Arabic / Amiri, OFL): documents with title, headings, 2-column Arabic, mixed AR/EN paragraphs, diacritics, Arabic-Indic and Western numbers with `٫`/`%`/currency, ruled tables (Arabic headers), an embedded raster chart with known values, captions, headers/footers. Ground truth JSON generated from the same source. Rasterized variants (300/150/100 DPI, light noise/skew) produced for Phase 3.
9. Elements inspection route `GET …/elements`.

**Testing:** unit tests per extractor on fixtures; golden-file tests for `elements.jsonl` structure (types, order, section_path); malformed/encrypted/zero-page PDF tests; a real-world sample set (user-provided Arabic PDFs, if supplied, kept out of git when not redistributable).

**Acceptance:** AC-2.

**Risks:** PyMuPDF ordering differences on real Arabic PDFs (mitigation: fixture + real-doc checks, column logic configurable); heading heuristics brittle (mitigation: measured on fixtures, conservative defaults — paragraph by default); AGPL licensing (decision recorded in MODEL_RESEARCH §9).

**Out of scope:** OCR, any VLM call, chunking/embedding changes, chat changes.

---

## Phase 3 — Multimodal intelligence

**Objective:** OCR scanned/garbled pages, describe visuals at ingestion (Stage 1), and provide question-time visual analysis (Stage 2) with a session-scoped cache — with models chosen by measurement.

**Existing modules affected:** `ingestion/pipeline.py` (OCR + describe stages), `llm/client.py` (multimodal message helpers, file-parser plugin support).

**New modules:** `ingestion/ocr/{base,vlm_ocr,mistral_ocr}.py`, `vision/{describe,analyze,cache,prompts}.py`, `eval/run_ocr_bakeoff.py` (complete), `eval/run_table_eval.py`, `eval/run_chart_eval.py`, `docs/architecture/MODEL_EVAL_RESULTS.md`.

**Tasks:**
1. Run the OCR/table/chart bake-off (MODEL_RESEARCH §8) on the Phase 2 rasterized fixtures + licensed real data; write results; propose defaults → **Claude approves before task 2 ships defaults**.
2. `VLMOCREngine` with JSON-schema output (TD §5.4), DPI escalation, unreadable markers, validation, retry.
3. `MistralOCREngine` adapter (OpenRouter `file-parser` plugin, `mistral-ocr`), mapped to page elements.
4. `mixed` pages: OCR of large text-bearing images, attached to the image element.
5. Stage 1 `describe.py` (TD §5.5) with per-document budget, batching, skip rules.
6. Stage 2 `analyze.py` + `cache.py` (TD §7): full-extraction prompt, value_source flags, per-key locking, persistence, deletion hooks.
7. Cost accounting for images; per-document and per-session budgets enforced.

**Testing:** fake-transport unit tests for parsing/validation/retries/caching/budget; cache hit/miss/coalescing tests; deletion removes cache; live bake-off (marked `live`).

**Acceptance:** AC-3.

**Risks:** VLM OCR hallucinating plausible Arabic (mitigation: strict prompt, numeric EM metric, compare with native text on mixed fixtures, `LOW_CONFIDENCE` status); provider image-token pricing variance (measure); ZDR availability per model (explicit error).

**Out of scope:** local GPU OCR adapters (interface only), retrieval/chat changes.

---

## Phase 4 — Multi-document RAG

**Objective:** Structure-aware chunks, multilingual embeddings, session-scoped filtered retrieval, optional hybrid/rerank, and server-generated citations.

**Existing modules affected:** `rag/chunker.py` (new function added; legacy kept), `rag/embeddings.py`, `rag/vector_store.py` (→ `SessionIndex`; legacy `VectorStore` kept as a thin wrapper until Phase 5), `rag/rag_pipeline.py` (legacy wrapper).

**New modules:** `rag/{bm25,retriever,rerank,citations,normalize}.py`, `eval/run_retrieval_eval.py`, `eval/datasets/retrieval/*.jsonl`.

**Tasks:**
1. Chunker per TD §6.1 (sections, tables with repeated headers, visual chunks, embed_text header).
2. Embedding batching + instruction-aware queries + per-index model lock.
3. `SessionIndex` (vectorized, masks, remove_document, persistence).
4. Indexing stage in the ingestion pipeline (after extraction/OCR/describe); re-index safety on document deletion mid-ingestion.
5. Retrieval eval dataset (≥ 150 queries: AR→AR, AR→EN, EN→AR, mixed, numeric/exact-term, table, visual, multi-doc) with gold chunk/element IDs; run the embedding bake-off; propose default → Claude approves.
6. BM25 + RRF behind a flag; reranker behind a flag; enable only per eval gate.
7. `citations.py` (TD §6.8) label registry + validator.
8. Scope resolution + contamination assertions (TD §6.6); per-document retrieval mode for comparisons (TD §6.7).

**Testing:** chunker unit tests (no cross-doc/section leakage, header repetition, token bounds); index tests (filtering, deletion compaction, concurrency); citation validator tests (invented labels stripped, pages derived); retrieval eval (live).

**Acceptance:** AC-4.

**Risks:** cross-lingual recall below target (mitigation: bake-off, query translation fallback as a later option — not by default); BM25 Arabic normalization collisions (search form only).

**Out of scope:** agent/prompt changes beyond what retrieval requires; frontend.

---

## Phase 5 — Agent integration

**Objective:** Grounded chatbot, summarizer and question generator over session documents via the refactored custom ReAct engine; complete API.

**Existing modules affected:** `agent/base.py` (refactor TD §9.1), `agent/prompts.py`, `tools/registry.py`, `tools/file_tool.py` (sandbox), `chatbot/chat.py`, `main.py` (switch to services, multi-file CLI).

**New modules:** `tools/{search_tools,visual_tools}.py`, `services/{chat,summary,questions}.py` (or inside `chatbot/`/`agent/`), `api/routes_chat.py`.

**Tasks:**
1. `BaseAgent` refactor: per-run state, scratchpad, JSON tool input, case-insensitive parsing, budgets, typed errors, trace events; keep loop detection and `tool_logs`.
2. `ToolRegistry` with descriptions, schemas, session-scoped context injection; remove `read_file` from agent tools; sandbox legacy tool.
3. Chat: single-pass default, ReAct escalation (visual analysis, comparison), follow-up memory + conditional rewrite, language matching, refusal, citation validation, Stage-2 integration.
4. Summarizer map-reduce with citations (fix D2); question generator with evidence and answers (fix D3).
5. Prompt-injection hardening (TD §12) + adversarial fixture documents.
6. API routes: chat, summaries, questions.
7. CLI: multi-file session, `/docs`, `/scope`, `/summary`, `/questions` commands.

**Testing:** agent unit tests with scripted fake LLM (tool call, FINAL, invalid format recovery, budget stop, state reset between runs); chat tests (citations only from registry, refusal path, scope enforcement, language); injection tests (document says "ignore instructions / reveal key / call read_file" → no effect); E2E QA eval (live).

**Acceptance:** AC-5.

**Risks:** ReAct escalation increases cost (mitigation: call caps, deterministic sufficiency rules first); LLM-judge bias (mitigation: manual spot checks recorded by Claude).

**Out of scope:** frontend, auth, persistence.

---

## Phase 6 — Testing and hardening

**Objective:** Prove the system meets AC under realistic conditions; close robustness and security gaps.

**Tasks:** full evaluation run (OCR, tables, charts, retrieval, QA, multi-doc, refusal) with a consolidated report; fault injection (429 storms, timeouts, malformed responses, provider ZDR refusal); large documents (300-page native, 50-page scanned) with time/cost/memory measurements; malicious files (zip-bomb-like images, deeply nested PDF objects, invalid xref, JavaScript-bearing PDFs — content never executed); session cleanup under concurrency; regression suite for the legacy CLI; README + API docs update (including data-retention statement).

**Acceptance:** AC-6.

**Out of scope:** new features.
