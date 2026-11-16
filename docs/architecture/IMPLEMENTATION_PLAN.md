# AgenticDoc — Phased Implementation Plan

**Planner/Reviewer:** Claude · **Implementer:** Codex · **Date:** 2026-11-16 (revised 2026-11-16: evaluation-first strategy)
References: [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) (TD), [EXTRACTION_LAB_DESIGN.md](EXTRACTION_LAB_DESIGN.md) (LAB), [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) (AC), [REPOSITORY_AUDIT.md](REPOSITORY_AUDIT.md) (defects D1–D20).

## 0. Strategy change (2026-11-16) — evaluation first

The user wants to test extraction tools and models on their own documents before the production pipeline is chosen. The execution order is now:

| Phase | Name | Status | Gate |
|---|---|---|---|
| **E1** | **Extraction Lab + text extraction evaluation** (native PDF text layers), in checkpoints E1-A → E1-D, each independently reviewed | **Issued 2026-11-16 — E1-A first** | AC-E1 (all 21 items) |
| E2 | Arabic OCR comparison of **self-hostable open models only**: mandatory NAMAA Qari-OCR (0.4.0, v0.3, 0.2.2.1), PaddleOCR-VL 1.6, PaddleOCR PP-OCRv5 (Arabic) and Qwen3-VL; plus Nuqta, AIN, DeepSeek-OCR, larger open VLMs (Qwen3.8-27B, Gemma 4, …) and Tesseract; dots.ocr and MinerU only with approval (Class B). Evaluation via OpenRouter / HF Inference Providers when the exact eligible model is hosted, otherwise local (SHM §1a). Hosted and local results both count. Plan: [E2_OCR_EVALUATION_PLAN.md](E2_OCR_EVALUATION_PLAN.md) | Planned (after E1) | AC-E2 (draft; finalized at kickoff) |
| E3 | Table extraction evaluation (self-hostable models only) | Planned | AC-E3 |
| E4 | Chart understanding evaluation (self-hostable VLMs only) | Planned | AC-E4 |
| **E4R** | **Retrieval and chatbot model evaluation (new, self-hosting requirement):** embeddings, rerankers and chat LLMs from SELF_HOSTED_MODEL_SELECTION §2.3–§2.5 on identical Arabic/English retrieval and QA sets, via hosted evaluation providers or local inference (SHM §1a), user review before any default | Planned (may run in parallel with E3/E4) | AC-E4R (defined at kickoff; draws on AC-4 items 2–4 and AC-5 item 3) |
| E5 | Select (user-approved models only) and integrate the validated pipeline into AgenticDoc, including the **inference gateway** (TD §0.1) with production egress enforcement | Planned; absorbs Phases 1–2 below | AC-E5 |
| 3–6 | Multimodal, multi-document RAG, agents, hardening (below) | **Deferred until after E5** | AC-3 … AC-6 |

### Self-hosting requirement (2026-11-16) — applies to E2 onward
- **Only downloadable, self-hostable, eligibly licensed models are evaluated** (policy and candidates: [SELF_HOSTED_MODEL_SELECTION.md](SELF_HOSTED_MODEL_SELECTION.md)). Proprietary API-only models are excluded from every phase.
- **Evaluation providers (clarification 2026-11-16, SHM §1a):** an eligible model may be evaluated through OpenRouter or Hugging Face Inference Providers (preferred when the exact model is hosted), or locally. Hosted and local results are both eligible for ranking, with `inference_source`, provider, quantization and settings recorded. API availability never establishes eligibility. No paid calls, large downloads or GPU rental without approval.
- **Production must run entirely inside company infrastructure:** the inference gateway with provider adapters (TD §0), an internal host allow-list in the production profile, and no external AI calls.
- **Before any weight download or GPU framework install:** a licence and hardware review per model (SHM §1, E2P §5), recorded and approved by the user.
- **Required input from the user:** the target company server specification (SHM §5). Rankings are reported per hardware profile the company can provide.
- **E1:** the OpenRouter file-parser adapter was **removed from E1-D** (user decision, CLAUDE_REVIEW Entry 6). Its engines (`cloudflare-ai`, `mistral-ocr`) are services, not downloadable models, so the 2026-11-16 clarification on evaluation providers doesn't bring them back. E1-A correction round 1 continues unchanged.

Consequences:
- **The former Phase 1 task ("Backend foundation") is withdrawn before implementation.** It is archived at `docs/handoff/archive/CODEX_TASK_phase1_foundation_SUPERSEDED.md`. Its content (OpenRouter client hardening, config, sessions, FastAPI) is reused in E5. The Lab's own small client and workspace code serve as prototypes for it.
- **No refactoring of `src/` during E1–E4.** The existing CLI must keep working unchanged.
- TD §5 (document processing) and the model choices in MODEL_RESEARCH §9 are now **hypotheses to be tested in the Lab**, not decisions. E5 updates them with measured evidence.
- The Phase 1–6 sections below stay as the post-E5 roadmap. They will be revised at E5 with the measured results.

### E1 — Extraction Lab + text extraction (summary; the task is in `docs/handoff/CODEX_TASK.md`)
- **Objective:** a local Streamlit lab where the user uploads PDFs/images, runs several text-layer extractors on the same pages, inspects them next to the page image, edits and verifies ground truth, and sees CER/WER (verified ground truth only), diagnostics, human-review records, timing and cost, then exports reports.
- **Existing modules affected:** none. A new package `Project sdaia/lab/` and `Project sdaia/tests/lab/`; root `.gitignore` additions.
- **Adapters:** PyMuPDF, pypdfium2, pdfplumber, pypdf (local). ~~OpenRouter file-parser~~ removed (user decision 2026-11-16).
- **Out of scope:** OCR/VLM adapters, tables, charts, any change to `src/`, a production frontend, RAG.
- **Risks:** synthetic fixtures produced by PyMuPDF may favour PyMuPDF's extractor (mitigation: real user documents, and fixtures from a second producer where possible, see LAB §7); Streamlit statefulness bugs (mitigation: all logic in `lab.core`, tested without Streamlit).

### E2–E4 (outline; detailed tasks issued after the previous phase is approved)
- **E2 (revised 2026-11-16; mandatory evaluation of self-hostable open OCR models, see SELF_HOSTED_MODEL_SELECTION):** add the `ocr` task, reusing E1 ComparisonSets and verified GT unchanged. Planned checkpoints:
  - **E2-A — Model manager & local runtimes:** licence/size/revision pre-download review with explicit per-model user approval; `LAB_MODELS_DIR` outside Git; `models.lock.json` hashes; pinned llama.cpp binaries; separate venvs for torch and paddle; worker protocol (local HTTP/stdio); peak RAM/VRAM sampling; a hardware report.
  - **E2-B — Local adapters:** Qari 0.4.0 (cloud-GPU reference via the official adapter + self-built, validated GGUF for local CPU), Qari v0.3, Qari 0.2.2.1, PaddleOCR-VL 1.6 (GGUF and the PaddleOCR pipeline), Nuqta 4B/0.8B, dots.ocr, Tesseract; AIN and DeepSeek-OCR via cloud GPU or a documented blocker.
  - **E2-C — Hosted evaluation providers and GPU runs (revised 2026-11-16, clarification):** adapters for OpenRouter and Hugging Face Inference Providers (OpenAI-compatible client, identity verification via `hugging_face_id`/repo ID, provider pinning, quantization recording, `inference_source` on every result, approval and spend guard for paid calls, fixtures-only by default). Plus an approved private/rented GPU runner (vLLM with pinned images/weights) for eligible models that are neither hosted nor runnable on the laptop. **Hosted and local results both count in rankings** (E2P §3). Proprietary models and `mistral-ocr` stay excluded.
  - **E2-D — Metrics & comparison:** reading-order Kendall τ (line-annotated GT), table-text accuracy (region-marked GT), value-equivalent numeric recall, latency, resources, cost, coverage, contamination flags; the E2 comparison view; `E2_OCR_RESULTS.md`; Claude's non-binding analysis; **the user's personal review and decision before any selection**.
  - A local candidate that is infeasible on the laptop (no NVIDIA GPU) is run on an approved cloud GPU, or listed with its blocker. It is never silently dropped.
- **E3:** add the `table` task: cell-grid ground-truth editor, cell EM / numeric cell EM / TEDS; adapters PyMuPDF `find_tables`, pdfplumber, best E2 VLMs, optionally Docling.
- **E4:** add the `chart` task: data-point ground truth with `printed`/`estimated` flags; printed-value EM, abstention rate, hallucinated-value rate; VLM adapters.
- **E4R (new):** a retrieval and chat bake-off of self-hosted embeddings (Qwen3-Embedding 0.6B/4B/8B, bge-m3 dense and sparse, multilingual-e5, gte, arctic-embed, GATE-AraBert), rerankers (Qwen3-Reranker, bge-reranker-v2-m3, mxbai, gte, GATE-Reranker) and chat LLMs (Qwen3/3.5/3.6/3.8, ALLaM-7B, Jais, Fanar after a base-licence check, gpt-oss, Gemma 4, Mistral Small 3.2). Uses AR→AR, AR→EN, EN→AR and grounded QA sets built from the verified E1/E2 documents. Evaluated through hosted evaluation providers where the exact model is served (OpenRouter serves Qwen3-Embedding 4B/8B, bge-m3, multilingual-e5-large, Qwen3-Reranker 0.6B/8B and most candidate LLMs; HF Inference serves Qwen3-Embedding-8B), otherwise locally via TEI/vLLM/llama.cpp. Records `inference_source` and documents a self-hosted serving recipe for every ranked model. User review before any default.
- **E5:** write `MODEL_EVAL_RESULTS.md` from the Lab exports, record the **user-approved** models in the registry (TD §0.3), update TD §5 with measured choices, then implement the foundation (former Phase 1, with the inference gateway replacing the OpenRouter client) and the validated extraction (former Phase 2/3 extraction parts) in `src/`. Production profile: internal hosts only.

## Ground rules for every phase
1. Work on a branch `phase-N-<slug>` from the latest approved `main`; one PR per phase (corrections go on the same branch).
2. Do not change interfaces defined in TD without a written proposal in `CODEX_REPORT.md` → "Design deviations", approved by Claude.
3. All model IDs, limits, TTLs from `src/config.py`. No hard-coded model strings outside config defaults.
4. Unit tests never call the network: use a fake transport for the inference gateway (formerly "the fake OpenRouter transport"). Live tests are marked `@pytest.mark.live` and skipped without `OPENROUTER_API_KEY`.
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
3. ~~`MistralOCREngine` adapter~~ (void, 2026-11-16: `mistral-ocr` is an external service excluded by the self-hosting requirement). Replaced by the self-hosted `OCREngine` adapters selected in E2 (TD §0.1).
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
