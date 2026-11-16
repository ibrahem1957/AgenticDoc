# AgenticDoc — Acceptance Criteria & Evaluation Strategy

**Owner:** Claude (defines and verifies) · **Date:** 2026-11-16
Thresholds marked **(provisional)** are calibrated once the Phase 3/4 baselines exist; Claude may tighten them but will not loosen them without recording the reason here. A phase passes only when **every** criterion is met *and* Claude's independent review (`docs/reviews/CLAUDE_REVIEW.md`) approves it. Codex's self-report is never sufficient.

## Evaluation strategy

| Layer | Data | Metric | Tooling |
|---|---|---|---|
| Unit | Synthetic inputs, fake OpenRouter transport | pass/fail | `pytest -m "not live"` (offline, deterministic, CI-safe) |
| Extraction | Synthetic PDFs with exact ground truth (Phase 2 generator), user-supplied real Arabic PDFs, licensed external sets | CER, WER, numeric exact match, element-type F1, reading-order Kendall τ, table cell EM, TEDS | `eval/run_extraction_eval.py`, `eval/run_ocr_bakeoff.py` |
| Visual | Synthetic charts (labeled/unlabeled, Arabic labels) | labeled-value EM, abstention rate, hallucinated-value rate | `eval/run_chart_eval.py` |
| Retrieval | ≥ 150 queries with gold element IDs (AR→AR, AR→EN, EN→AR, mixed, numeric, table, visual, multi-doc) | Recall@1/5/10, MRR@10 | `eval/run_retrieval_eval.py` |
| End-to-end QA | ≥ 60 items: answerable single-doc, multi-doc comparison, conflicting values, chart-dependent, unanswerable, follow-up | correctness, citation validity, citation support, refusal accuracy, language match, cost/latency | `eval/run_qa_eval.py` (LLM judge + Claude manual spot-check of ≥ 20 items) |

Metric definitions (in `eval/metrics.py`, unit-tested):
- **CER/WER**: Levenshtein distance / reference length on NFC-normalized text with whitespace collapsed; diacritics **kept** (report a diacritics-stripped CER as a secondary metric).
- **Numeric exact match**: every number token in the reference (Arabic-Indic or Western digits, with `.`/`٫`/`,`/`٬`, `%`/`٪`, currency) must appear **identically** in the output (no digit-form conversion) — recall over reference numbers; also report precision (numbers in output not in reference = possible hallucination).
- **Reading order**: Kendall τ between reference and predicted block order.
- **Table cell EM**: fraction of reference cells whose (row, col, normalized text) matches.
- **Citation validity**: fraction of citations that map to a chunk actually retrieved for that answer (must be 100% by construction).
- **Citation support**: fraction of cited claims judged supported by the cited chunk.

---

## Evaluation-first status (2026-11-16)
The phase order is E1 → E5, then Phases 3–6 (IMPLEMENTATION_PLAN §0). **AC-E1 is the active gate.** AC-1 and AC-2 are deferred to E5, where they will be revised with the Lab's measured results. AC-3 … AC-6 are deferred until after E5. AC-E2 … AC-E5 are written at the kickoff of each phase.

## AC-E1 — Extraction Lab + text extraction evaluation

Verification: Claude re-runs every command and walks through the UI checklist (item 15) personally. "Offline" means with network disabled or `OPENROUTER_API_KEY` unset.

**Checkpoints (user decision, 2026-11-16):** E1 is implemented in checkpoints E1-A … E1-D (CODEX_TASK §9), each reviewed by Claude before the next starts. **All 21 items below stay mandatory for E1 completion.** The checkpoint mapping only sets when each item is verified. Two clarifications, neither of which removes an item:
- **Optional file parser:** a missing API key or unusable file-parser output does not block acceptance of the offline lab. Item 15h and the live part of item 16 are then satisfied by the documented fallback: adapter `enabled=false` with the reason shown, all offline tests passing, and the status recorded as "not run (no key)". Claude runs the live check when a key is available.
- **Real Arabic documents:** checkpoints are reviewed on reproducible fixtures. The real-document parts of items 15 and 19 are verified in the final manual evaluation with documents the user uploads. E1 is complete only after that evaluation.

**Isolation and existing app**
1. `git diff main -- "Project sdaia/src"` is empty. `python -m src.main` behaves as before (no new imports, no new required dependencies in the main app).
2. `lab.core` contains no `streamlit` import (`grep -rn "import streamlit\|from streamlit" "Project sdaia/lab/core"` → no matches). `src` contains no `lab` import.
3. Lab dependencies are installed only via `lab/requirements-lab.txt`. `pip install -r lab/requirements-lab.txt` succeeds on Python 3.11–3.13 (Windows and Linux) without a GPU or model downloads.

**Tests**
4. `pytest tests/lab` passes offline. Coverage of `lab/core` ≥ 85% (`--cov=lab.core`). `ruff check lab tests/lab` passes.
5. Metric unit tests use hand-computed values and cover: identical strings (0), empty hypothesis (CER = 1), Arabic with diacritics (`مُحَمَّد` vs `محمد`: CER > 0, CER-no-diacritics = 0), Arabic-Indic vs Western digits (`٢٠٢٥` ≠ `2025` in numeric match), `٣٫٥` and `١٢٫٥٪` tokenized as single numbers, reversed word order (BoW F1 = 1, WER > 0), and micro-averaging across pages.

**Fixtures**
6. `python -m lab.fixtures.generate_fixtures` deterministically produces at least: EN single-column; AR single-column; AR with full diacritics; mixed AR/EN with Arabic-Indic and Western numbers, `٫`, `%`/`٪`, currency; AR two-column; AR with running header/footer and page numbers; an image-only page PDF (no text layer); a multi-page (≥ 5 pages) document; one PNG image. Each comes with per-page ground-truth JSON holding the **visibly rendered source text** (`source="fixture"`, `verified`), a page-1 PNG render for visual verification, and metadata `producer`, `producer_version` and `font`. Arabic fixtures are produced by PyMuPDF and, when a Chromium browser is installed, also by headless Chromium (LAB §7). At least one PyMuPDF-produced Arabic fixture shows `presentation_forms > 0`, and `arabic_fold` reduces it to 0 (test).
7. On the fixtures, the suite reports per adapter per fixture CER/WER/BoW-F1/numeric recall-precision, wall_ms, cpu_ms. The **values themselves are evidence, not pass/fail**, except: every local adapter produces a `RunResult` (ok, empty or error) for every fixture with no crash or hang; the image-only PDF yields `status="empty"` with the diagnostic "no text layer"; the PNG yields `not_applicable`.

**Behaviour**
8. **Ground-truth gating:** metrics are computed only for `verified` GT pages. A draft page yields no metric (test). Aggregates show `verified k/n`. Editing a verified page makes it draft, increments the version and marks old metrics stale (test).
9. **Seeding bias flag:** GT seeded from adapter X sets `seeded_from`, and X's metrics on those pages carry the bias flag (test + UI).
10. **No external call without action:** with external APIs toggled off, no HTTP request is made by any code path (test using a transport that fails on any call). With it on, an API run needs a confirmation object containing file sha256, page list, engine, model and estimate. A run without it raises (test). Spend guards block over-limit estimates (test).
11. **Secrets:** the API key never appears in workspace files, exports, logs or rendered UI (test: run with a sentinel key, then grep the workspace dir, exports and captured logs).
12. **Temporary storage:** "End workspace" deletes the workspace directory. The TTL sweep deletes workspaces older than the TTL (injectable clock test). Uploaded filenames never appear in disk paths (test with `../../x.pdf` and an Arabic filename `تقرير ٢٠٢٥.pdf`). Exports exclude originals and extracted text unless their checkboxes are ticked (test).
13. **Robustness:** a malformed PDF, an encrypted PDF, and a timeout (adapter stub that sleeps) each produce a clean `error`/`timeout` `RunResult`. The UI keeps working and other adapters still run (tests).
14. **Reproducibility:** each `RunResult` records library version, params, variant, doc sha256 and environment. Re-running with identical inputs is a cache hit. "Re-run" bypasses the cache. Export → import of a bundle restores GT, reviews and results, and refuses a mismatched sha256 (tests).

**UI walkthrough (manual, performed by Claude and the user)**
15. In `streamlit run lab/app/Home.py` (bound to 127.0.0.1):
  a. upload a fixture PDF, a real Arabic PDF and a PNG;
  b. run all 4 local adapters with all 4 variants (`raw`, `arabic_fold`, `bidi_reorder`, `bidi_reorder+arabic_fold`) on chosen pages, and see variants computed without re-extraction;
  c. in Compare, see the page image beside each result; Arabic renders RTL; the block-order overlay works for PyMuPDF, pypdfium2 and pdfplumber; the word diff vs GT and vs another run renders;
  d. seed GT from one output, edit it, verify it, and see metrics appear only after verification;
  e. submit a human review;
  f. see the three tables (automatic metrics / diagnostics / human review) kept separate, plus timing;
  g. export a bundle, end the workspace, start a new one, import the bundle;
  h. with a key configured and external APIs enabled, run `text.openrouter_fileparser` with `cloudflare-ai` on a 1-page fixture, see the confirmation dialog, then usage and cost with `cost_source`. If no key is available, Codex states "not run" and Claude runs it.
16. **File-parser fact check:** Codex's report states, with a captured redacted response excerpt, whether `annotations[].file.content` contains the parsed text and whether it has page delimiters. If the text isn't available, the adapter ships `enabled=false` with the reason shown in the UI.

**User requirements R2–R5, R8 (confirmed 2026-11-16)**
17. **Raw vs cleaned (R2):** every variant result references its raw run, and the raw text is byte-identical before and after variants are computed (test). In Compare, RAW and CLEANED panes are separate and labelled, and raw stays visible whenever a cleaned pane is shown (UI walkthrough). Exports contain raw and every cleaned variant as separate records.
18. **Same pages, same reference (R3):** every run in a `ComparisonSet` covers the identical page list of the identical document (sha256) and is scored against the same frozen GT version per page. Mixing runs with different `page_set_hash` raises `IncomparableRunsError`. A GT edit marks the set stale and re-scores all its runs together. Every metric row carries `set_id` and `page_set_hash` (tests).
19. **Real-world Arabic documents (R4):** `pdf_producer`/`pdf_creator` are captured from uploaded PDFs, and `page_tags` can be set per page. Reports break metrics down by tag and producer, with "insufficient data" below 3 verified pages (tests). The UI walkthrough uses at least one real multi-column Arabic PDF with headings, numerals and diacritics supplied by the user, and at least two different producers across the walkthrough documents.
20. **E2 preserved, no OCR verdict (R5):** `report.md` contains the fixed scope statement (LAB §11a) verbatim. A test fails if any report contains "winner", "best OCR" or "recommended pipeline". E2 candidate pages are listed. ComparisonSets and verified GT are stored so E2 adapters can be scored against them unchanged (round-trip test on the stored set).
21. **Individual error inspection (R8):** for verified pages, `ErrorItem`s are produced with op, spans, ±30-char context, offsets and categories. Hand-built tests cover letter substitution, missing diacritic, `digit_form` (`٢٠٢٥`→`۲۰۲٥`), `transpose_suspect` (`٢٠٢٥`→`٥٢٠٢`), a reversed word and inserted Latin text. The number check list reports found / missing / altered / extra. In the UI walkthrough, the Errors page filters by category and highlights the selected span in both texts, and `errors.csv` is exported.

## AC-1 — Backend foundation (deferred to E5)
1. `pip install -e ".[dev]"` (or `pip install -r requirements-dev.txt`) succeeds on Python 3.11–3.13 from `Project sdaia/`.
2. `pytest -m "not live"` passes with **no network access**; coverage of `src/llm`, `src/sessions`, `src/documents` ≥ 85%.
3. `ruff check src tests` passes.
4. All model IDs and limits come from `src/config.py`; `grep -rn "openai/\|google/\|qwen/" src --include=*.py` matches only `config.py`.
5. `OpenRouterClient`: timeouts on every request; retries only on 429/5xx/timeouts with backoff honoring `Retry-After`; no retry on 4xx auth/validation; typed exceptions; API key never present in logs or exception messages (test asserts on captured logs).
6. Every request carries the `provider` privacy object (`data_collection: "deny"` default; `zdr` when configured).
7. Usage ledger records model, tokens, cost (actual or estimated, with `cost_source`), latency, status per call; aggregated per session.
8. Legacy `OpenRouterLLM.invoke()` and `OpenRouterEmbeddings.embed()` keep their signatures and behavior; `python -m src.main` still runs end-to-end on `src/data.txt` (manual run documented in the report, live).
9. Sessions: create/get/delete; idle and absolute expiry; sweeper removes expired dirs; startup removes orphaned dirs; expired session → 410/404 per TD §8; tests use an injectable clock.
10. Upload: magic-byte validation; oversize → 413; unsupported → 415; filename never used in disk path; stored under `sessions/{sid}/documents/{did}/`; listing and deletion work; deleting removes the directory; cross-session access to a document → 404.
11. No document content logged at INFO (test with a sentinel string in an uploaded file).
12. `eval/metrics.py` CER/WER/numeric-EM/Kendall-τ/table-cell-EM implemented with unit tests on hand-computed examples, including Arabic with diacritics and Arabic-Indic digits.
13. `.gitignore` excludes `__pycache__`, `.env`, temp dirs, `eval/results/raw`; committed `.pyc` files removed from git.

## AC-2 — Deterministic extraction
1. Native synthetic Arabic PDFs: CER ≤ **1.0%**, WER ≤ **3%**, numeric EM = **100%** (digit forms preserved).
2. Mixed Arabic/English paragraphs: CER ≤ 1.5%; English runs not reversed; Arabic runs not reversed.
3. Reading order on two-column Arabic fixtures: Kendall τ ≥ **0.95**.
4. Element typing on fixtures: heading F1 ≥ 0.90, table detection recall ≥ 0.95 (ruled tables), caption linking accuracy ≥ 0.90, header/footer detection ≥ 0.90.
5. Native ruled tables: cell EM ≥ **0.95**, numeric cell EM = 100%, RTL column order correct.
6. Page classification on fixtures (native/scanned/mixed/garbled): accuracy ≥ 0.95; zero native pages misrouted to OCR in the native set.
7. Every element has `document_id`, `page`, `element_type`, `reading_order`, `provenance`; native elements have `bbox`; `element_id`s unique and stable across re-runs.
8. No text duplicated between table elements and paragraph elements (overlap test).
9. Malformed, encrypted, zero-page and oversized PDFs end in `failed` with a clear error, never an unhandled exception or HTTP 500.
10. Zero OpenRouter calls during Phase 2 ingestion (asserted with fake transport call counter).

## AC-3 — Multimodal (provisional thresholds)
1. Bake-off results committed (`MODEL_EVAL_RESULTS.md` + raw outputs); defaults approved by Claude before merge.
2. Scanned synthetic Arabic at 300 DPI: CER ≤ **3%**, WER ≤ **10%**, numeric EM ≥ **98%**; at 150 DPI: CER ≤ 6%; at 100 DPI: reported, and every page either meets CER ≤ 10% or is flagged `LOW_CONFIDENCE`/`UNREADABLE`.
3. Scanned tables: cell EM ≥ 0.85, numeric cell EM ≥ 0.95.
4. Charts with printed values: value EM ≥ **0.90**. Charts without printed values: **0 fabricated exact values** — every value is `estimated_from_axis` or `unreadable`.
5. Native pages are never sent to OCR (call counter); visual calls ≤ configured budget per document.
6. Stage-2 cache: second identical analysis → 0 API calls; concurrent identical requests → 1 API call; deleting the document removes its cache files and entries.
7. Every OCR/vision element records model, prompt_version, method, status.
8. API failures in OCR mark affected pages `failed`/`partial` and the document `partial`, not the whole session failed.

## AC-4 — Multi-document RAG (provisional thresholds)
1. Chunks never span two documents; never span sections except by the merge rule; large-table chunks repeat headers.
2. Retrieval (selected embedding default, live eval): Recall@5 ≥ **0.90** AR→AR, ≥ **0.80** cross-lingual (AR↔EN), ≥ 0.90 numeric/exact-term queries (hybrid allowed); MRR@10 reported for all.
3. Embedding default beats or matches `openai/text-embedding-3-small` on the Arabic sets (or the reason for keeping the baseline is documented).
4. Hybrid and reranking enabled by default only if they improve Recall@5 or MRR@10 by ≥ 5 points on the Arabic + cross-lingual sets without exceeding latency p95 + 1 s.
5. Scope: 0 out-of-scope chunks across 1,000 randomized scoped queries (property test, offline with fake embeddings); cross-session access impossible.
6. Document removal: after deletion, 0 chunks/vectors/BM25 entries/visual cache entries/files remain for that document; other documents' results unchanged (test compares before/after).
7. Citation validator: invented labels removed and warned; `Citation` filenames/pages always derived from the registry (100% validity).
8. Comparison mode retrieves from every scoped document (each document contributes ≥ 1 chunk when relevant content exists).

## AC-5 — Agents & API
1. `BaseAgent`: per-run state reset (test: same instance, two runs, no false loop stop); scratchpad preserved across steps; budgets enforced; LLM errors produce `status="error"`, never error text as an answer.
2. Agent-exposed tools cannot access paths outside the session; `read_file` not exposed to agents; sandboxed legacy tool rejects `../` traversal (test).
3. QA eval (live): answer correctness ≥ **0.85**, citation validity **1.00**, citation support ≥ **0.90**, refusal accuracy on unanswerable ≥ **0.90**, false refusal ≤ 0.10, language match ≥ **0.98**.
4. Conflicting-value items: both values reported with their respective sources in ≥ 0.90 of cases; no averaging/reconciling.
5. Chart questions: no exact value stated where the evidence marks it estimated/unreadable (0 violations).
6. Follow-up items resolved correctly ≥ 0.80.
7. Summaries cover every top-level section (coverage check: each section cited at least once for documents ≤ 50 pages); generated questions each carry an answer and a valid citation; no duplicates.
8. Prompt-injection fixtures: 0 cases of following embedded instructions, revealing config/keys, or calling tools outside scope.
9. Cost/latency per chat answer recorded; median LLM calls per question ≤ 2; max ≤ 4.
10. All API endpoints in TD §10 implemented with the error envelope; OpenAPI schema generated.

## AC-6 — Hardening
1. All AC-2..AC-5 metrics re-run on the final code and reported together.
2. 300-page native PDF ingested within 5 min on a laptop CPU (excluding network), peak RSS ≤ 1.5 GB; 50-page scanned PDF completes with cost reported.
3. Fault-injection suite (429 storms, timeouts, malformed JSON, 5xx, ZDR refusal) passes: no crash, correct statuses, bounded retries.
4. Malicious-file suite passes (no hang > per-page timeout, no unbounded memory).
5. Sessions under concurrency (10 sessions × 3 documents, parallel deletes) leave no orphaned files after the sweeper runs.
6. Legacy CLI regression test passes.
7. README documents setup, configuration, limits, and the third-party data-retention statement.
