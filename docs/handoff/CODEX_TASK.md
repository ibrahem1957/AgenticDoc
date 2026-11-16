# CODEX TASK — Phase E1: Extraction Lab + Text Extraction Evaluation

**Issued by:** Claude (architect/reviewer) · **Date:** 2026-11-16 · **Status:** ISSUED 2026-11-16 (approved by the user with conditions, see §9). Implement **one checkpoint at a time**, starting with E1-A.
**Branch:** create `phase-e1-extraction-lab` from **`planning/multimodal-rag`** (not from `main`). **Never merge into `main`**, and never merge any branch yourself.
**Design (authoritative):** `docs/architecture/EXTRACTION_LAB_DESIGN.md` (LAB). **Acceptance:** `docs/architecture/ACCEPTANCE_CRITERIA.md` → **AC-E1** (items 1–21).
**Context:** `docs/architecture/IMPLEMENTATION_PLAN.md` §0 (strategy), `MODEL_RESEARCH.md` (candidates, NAMAA findings — relevant from E2).

---

> **Revision 2026-11-16 (user decision, self-hosted-only policy):** everything about OpenRouter is **void for E1**: the `text.openrouter_fileparser` adapter, `core/openrouter.py`, `core/costs.py`, the carrier model, API toggle, confirmation dialog, spend guards, `openrouter_base_url`/`require_zdr`/cost settings, the `test_fileparser_adapter`/`test_costs`/`test_live_fileparser` tests, and AC-E1.15h/16. Where §1–§8 still mention them, ignore those parts. The E1 lab makes no network calls. See §9 → E1-D.
>
> **Revision 2026-11-16 (Claude, LAB §4 contract additions):** `RunResult` gains `raw_run_id: str | None = None` and `variant_version: str | None = None`. `MetricResult` gains `variant: str = "raw"`, `set_id: str | None = None`, `page_set_hash: str | None = None` and `gt_seeded_from_this_run: bool = False`. They are optional with defaults, so E1-A's files stay valid. They are added in E1-B (raw/cleaned linkage, AC-E1.17; seeding bias, AC-E1.9) and used in E1-C (AC-E1.18).

## User requirements this task must satisfy (confirmed 2026-11-16)
| # | Requirement | Where specified | Verified by |
|---|---|---|---|
| R1 | Upload own Arabic PDFs; compare the original page visually against each extractor's output | LAB §3, §5.4, §10 | AC-E1.15a/c |
| R2 | Raw and cleaned text kept and shown separately | LAB §5.2, §10 | AC-E1.17 |
| R3 | All extractors scored against the same verified reference and identical pages | LAB §8.1 | AC-E1.18 |
| R4 | Real-world Arabic documents: multi-column, headings, paragraphs, numerals, diacritics, different producers | LAB §4 (`page_tags`, `pdf_producer`), §11a | AC-E1.6, AC-E1.19 |
| R5 | E2 comparison against OpenRouter vision models preserved; no winning Arabic OCR solution declared from E1 | LAB §11a, §12 | AC-E1.20 |
| R6 | Lab independent of the production RAG pipeline | §0 below | AC-E1.1–2 |
| R7 | No automatic uploads or paid API calls (since 2026-11-16: no external calls at all in E1) | LAB §1.2, §6 (superseded) | AC-E1.10 (revised) |
| R8 | Inspect individual errors, not only summary metrics | LAB §8.2 | AC-E1.21 |

## 0. Hard constraints
1. **Do not modify anything under `Project sdaia/src/`.** `python -m src.main` must behave exactly as before.
2. Everything new goes in `Project sdaia/lab/` and `Project sdaia/tests/lab/`, plus additions to the root `.gitignore` and a short "Extraction Lab" section at the end of the root `README.md`.
3. `lab/core/` must not import `streamlit`. `lab` must not import `src`.
4. **Phase E1 scope only:** the `text` task with native text-layer extractors. Don't implement OCR, VLM, table or chart adapters. Register those tasks as "planned" placeholders only (LAB §12).
5. **No network call without explicit user action** (LAB §1.2, §6). Unit tests never touch the network. Use `@pytest.mark.live` for the one optional live test.
6. **No GPU, no model downloads.**
7. Never log, store, export or display the API key. Never log document text.
8. If the design conflicts with reality (a library API differs, or OpenRouter's response shape differs), **do not improvise silently**. Implement the closest safe behaviour and record it under "Design deviations" in `CODEX_REPORT.md`.

## 1. Setup
- `lab/requirements-lab.txt`, with minimum versions pinned to releases at least 2 weeks old. Versions observed on PyPI on 2026-11-16 are given for reference only; pick what you install and record it:
  `streamlit` (1.67.0, Apache-2.0), `pymupdf` (2.1, AGPL-3.0), `pypdfium2` (5.15.2, Apache-2.0/BSD), `pdfplumber` (0.11.10, MIT), `pypdf` (7.1.0, BSD-3), `python-bidi` (LGPL-3.0, used unmodified as a library, for the `bidi_reorder` variant), `rapidfuzz` (MIT), `pydantic>=2`, `requests`, `python-dotenv`, `pillow`.
  Dev: `pytest`, `pytest-cov`, `ruff`.
- `lab/.streamlit/config.toml`: `server.address = "127.0.0.1"`, `browser.gatherUsageStats = false`, `server.maxUploadSize = 50`.
- Run from `Project sdaia/`: `streamlit run lab/app/Home.py`. Tests: `pytest tests/lab`.
- Root `.gitignore` adds `__pycache__/`, `*.pyc`, `.env`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `**/lab/fixtures/generated/`, `**/lab_exports/`. Do **not** `git rm` the existing committed `.pyc` files. That is a `src/` change and is deferred to E5.

## 2. Configuration
- `lab/config/lab.toml` (parsed with `tomllib`): `tmp_dir` (empty = OS temp + `agenticdoc-lab`), `workspace_ttl_hours = 24`, `max_file_mb = 50`, `max_pages = 200`, `max_documents = 30`, `viewer_dpi = 110`, `adapter_timeout_s = 120`, `external_api_default = false`, `require_zdr = false`, `max_cost_per_run_usd = 0.50`, `max_cost_per_workspace_usd = 2.00`, `openrouter_base_url = "https://openrouter.ai/api/v1"`.
- `lab/config/adapters.toml`: one table per adapter: `id`, `task`, `label`, `kind`, `module`, `enabled`, `preselected`, `params` (defaults + allowed values), and for API adapters `engine_options`, `carrier_model` (default: a cheap text model **that you verify exists** in `GET /api/v1/models` on the day you implement; record the ID and price in the report), `prices` (USD per token for the carrier; `mistral-ocr` = 0.002 per page).
- `lab/core/settings.py`: loads both files and allows env overrides `LAB_TMP_DIR` and `OPENROUTER_API_KEY` (via `python-dotenv`, looking for `.env` in `Project sdaia/`). It exposes `api_key_configured: bool`, **not** the key, to the UI layer. The key is read only inside the OpenRouter client.

## 3. Core modules (`lab/core/`) — implement per LAB §3–§11
| Module | Requirements |
|---|---|
| `models.py` | All contracts in LAB §4, exactly, with `schema_version = 1` on persisted files. |
| `workspace.py` | LAB §3: create/attach/list-recent/end; ID-only paths with `is_relative_to` checks; TTL sweep with injectable clock; atomic JSON writes (write temp file, then `os.replace`). |
| `ingest.py` | Magic-byte detection for PDF/PNG/JPEG/TIFF/WebP; streaming size cap; sha256; filename sanitization (NFC, strip control and bidi-override characters U+202A–202E and U+2066–2069, strip path separators, ≤ 255 chars, Arabic preserved); PDF page count and sizes via pypdfium2 (encrypted or malformed → clear `IngestError`); cheap per-page text-layer probe (pypdfium2 char count > 0); PDF Info `Producer`/`Creator` stored verbatim (`None` if absent); user-editable `page_tags` (LAB §4); lazy page PNG render at `viewer_dpi`, capped at 4,000 px on the longest side. Images: size check, `Image.MAX_IMAGE_PIXELS` cap, single "page". |
| `adapters/base.py`, `registry.py` | Protocol in LAB §5.1; registry builds `AdapterInfo` from the toml; a failed import marks the adapter unavailable with the reason; library version via `importlib.metadata`. |
| `adapters/text_pymupdf.py` | `get_text("text", sort=params.sort)` per page; blocks from `get_text("blocks")` (text blocks only) in returned order with bbox. |
| `adapters/text_pypdfium2.py` | `textpage.get_text_range()` per page; blocks = lines reconstructed from char boxes **only for the overlay** (the text field is exactly the library output). Use the API of the installed version. |
| `adapters/text_pdfplumber.py` | `extract_text(layout=params.layout, x_tolerance=params.x_tolerance)`; blocks from `extract_words()` grouped by line (`top` tolerance), in library order. |
| `adapters/text_pypdf.py` | `extract_text(extraction_mode=params.mode)`; no blocks. |
| `adapters/text_openrouter_fileparser.py` | LAB §6. Chat Completions with a `file` content part (base64 data URL of the original PDF, or of the selected pages extracted into a temporary PDF; use pypdfium2 or pypdf to build it, and record which) and `plugins: [{"id": "file-parser", "pdf": {"engine": <engine>}}]`; `provider` privacy object; carrier prompt "Reply with OK."; `max_tokens` 5. Parse `choices[0].message.annotations[]` where `type == "file"` → join `file.content[]` text parts. Page mapping per LAB §5.5. Use the usage fields actually returned. **Verify the request/response shape against the live docs on the day of implementation and quote the relevant doc lines in the report.** |
| `adapters/postprocess.py` | Variants `raw`, `arabic_fold`, `bidi_reorder`, `bidi_reorder+arabic_fold` (LAB §5.2), as pure, versioned functions computed from the stored raw output, with tests. Include a regression test built from the probe outputs in `docs/architecture/evidence/e1_probe/probe3_output.txt`: the pdfplumber/Edge case must improve under `bidi_reorder+arabic_fold`, and the pypdfium2/Edge case must get worse under `bidi_reorder`. That shows variants aren't applied globally. |
| `runner.py` | LAB §5.3: spawn-context child process per local adapter run, timeout, timing inside the child (`perf_counter`, `process_time`), cache key and lookup, re-run bypass, repeat ×N (local only, median reported, raw timings stored), sequential execution, progress callback. API adapters run in-process via the client and require a `ConfirmationToken` (doc sha256, pages, adapter, engine, model, estimate, timestamp) created by the UI after the dialog; no token → `PermissionError`. |
| `openrouter.py` | Minimal client: `GET /models` (public, cached 1 h in memory), `POST /chat/completions`; timeouts 10 s / 180 s; ≤ 2 retries on 429/5xx honoring `Retry-After`; typed errors; redaction of the key from any message; an injectable transport for tests; a `NoNetworkTransport` that raises on use (used by tests and whenever external APIs are off). |
| `costs.py` | Usage ledger (`ledger.jsonl` in the workspace); `estimate()` per adapter; spend guards (LAB §6); model availability check via the catalog. |
| `diagnostics.py` | LAB §4 `Diagnostics`, including ligature, digit-form-by-script and detached-diacritic counts (failure modes observed in LAB §7). `suspected_reversed_arabic` is a labelled heuristic: the share of Arabic words that start with a letter form that is typical only word-finally (e.g. `ة`, `ى`) or end with a word-initial-only pattern. Present it as a hint, never as accuracy. Unit-test the counts. |
| `metrics.py` | LAB §8 exactly, with `rapidfuzz.distance.Levenshtein` on strings and on token lists, plus the numeric tokenizer. Micro-averaged aggregates. Refuse to compute against non-verified GT pages (return `None` and a reason). |
| `comparison.py` | LAB §8.1: build a `ComparisonSet` for each multi-adapter/variant run on one page selection; freeze GT versions at scoring; mark sets stale when GT changes and re-score all runs together; refuse to put runs with different `page_set_hash` in one table (raise `IncomparableRunsError`); compute per-`page_tag` and per-`pdf_producer` breakdowns ("insufficient data" below 3 verified pages); list "E2 candidate" pages (no text layer, or every local adapter/variant CER above the configurable `e2_candidate_cer` threshold, default 0.10). |
| `errors.py` | LAB §8.2: Levenshtein opcodes → merged spans → `ErrorItem` with ±30-char context and categories (including `digit_form` and `transpose_suspect`); number check list (found / missing / altered with form / extra). Verified GT pages only. |
| `groundtruth.py` | LAB §9: create, edit (version++, verified → draft), verify, seed-from-run (sets `seeded_from`), import from `.txt` with form-feed (`\f`) page splits or from JSON, export; sha256 match is enforced. |
| `review.py` | `HumanReview` CRUD per run/page. |
| `report.py` | LAB §11: `results.json`, `metrics.csv`, `errors.csv`, `timing_cost.csv`, `reviews.csv`, `report.md` (one section per ComparisonSet; automatic metrics / diagnostics / human review in **separate sections**; verified-page counts; adapter versions and params; breakdowns by page tag and PDF producer; E2 candidate pages; limitations; and **verbatim** the fixed scope statement from LAB §11a). The report must not contain words like "winner", "best OCR" or "recommended pipeline" (test). `bundle.zip` with opt-in originals and extracted text; import with sha256 checks. |

## 4. Fixtures (`lab/fixtures/`)
- `generate_fixtures.py` produces the AC-E1 item 6 set into `lab/fixtures/generated/` (git-ignored), deterministically, with per-page ground truth JSON (`source="fixture"`, `verified`).
- **Read LAB §7 first.** The probe showed that generated Arabic PDFs do **not** round-trip: their text layers contain presentation forms, ligatures and substituted digit forms, and these depend on producer and font.
- **Ground truth = the source text that is visibly rendered**, not the text layer. Don't "correct" the ground truth to match what the PDF encodes.
- **Producers:** generate each Arabic text fixture with (1) PyMuPDF `insert_htmlbox` (`dir="rtl"`) using the committed OFL font, and (2) a headless Chromium (`msedge`, `chrome` or `chromium` found on PATH or in standard install locations) with `--print-to-pdf`, **only if one is already installed**. Otherwise skip it with a logged notice; never download a browser. Record `producer`, `producer_version` and `font` in each fixture's metadata. The bench report groups results by producer.
- **Verify visual correctness, not text-layer correctness:** for each generated fixture, render page 1 to PNG and save it next to the fixture, so the reviewer can confirm the rendered text matches the ground truth visually (shaping, RTL, digits). Claude reviews these PNGs in the PR.
- Presentation forms and ligatures are expected to appear in the text layer of generated fixtures anyway (LAB §7). No dedicated presentation-form fixture is required. Instead, the test suite asserts that `diagnostics.presentation_forms > 0` for at least one PyMuPDF-produced Arabic fixture, and that `arabic_fold` reduces that count to 0.
- The image-only fixture is a page containing only a raster image of text, with no text layer.
- Commit the font file under `lab/fixtures/fonts/` with its OFL licence text, after checking the licence permits redistribution (it does for OFL; quote it).
- Small committed test fixtures: 2–3 tiny PDFs (< 50 KB each) under `tests/lab/data/` so the tests don't depend on the generator.

## 5. Streamlit UI (`lab/app/`) — LAB §10
Keep it minimal and functional; the visual polish isn't evaluated. Requirements:
- All state through `lab.core`. Streamlit pages hold no business logic beyond wiring.
- Text panes: render escaped text inside `<div dir="auto" style="white-space: pre-wrap; unicode-bidi: plaintext">`. Toggles: monospace, show invisibles (render ZWJ/ZWNJ/RLM/LRM/NBSP/presentation forms as visible markers).
- Block overlay: draw numbered rectangles on the page PNG with Pillow (coordinates scaled from points to pixels).
- Word diff: `difflib.SequenceMatcher` on token lists, rendered as escaped spans with insert/delete styling; `dir="rtl"` when the reference is mostly Arabic.
- API confirmation: modal or expander with the facts from LAB §6, a checkbox and a button. The resulting `ConfirmationToken` is valid for that single run.
- **Documents page:** shows PDF producer/creator; lets the user set `page_tags` per page.
- **Raw vs cleaned:** in Compare, every column shows the RAW text and, if a variant is selected, the CLEANED text in a separate labelled pane (LAB §10). They're never merged, and raw stays visible.
- **Same pages / same reference:** the Run page creates one ComparisonSet per page selection. Compare, Errors and Results always work on one selected ComparisonSet, and show its pages and GT versions in a header.
- **Errors page** (LAB §8.2): filters (category, op, run, variant), list with context, click-to-highlight in both texts, per-category counts, number check list.
- Results page: per ComparisonSet, three separate tables + timing/cost table + tag/producer breakdowns + E2 candidates; download buttons for each export.

## 6. Tests (`tests/lab/`, offline) — minimum set
`test_models.py`, `test_workspace.py` (paths, traversal, TTL, end), `test_ingest.py` (magic bytes, limits, encrypted/malformed, Arabic filenames), `test_adapters_local.py` (each adapter on committed fixtures: returns a PageResult per page; image-only → empty; PNG → not_applicable), `test_postprocess.py`, `test_runner.py` (timeout via a sleeping stub adapter, crash isolation via a stub that raises, cache hit/bypass, repeat ×N), `test_fileparser_adapter.py` (fake transport: request contains plugin + provider object + file part; annotations parsed; no-annotation response → clear error; missing confirmation → PermissionError; external-off → NoNetworkTransport never called), `test_costs.py` (estimates, guards, ledger), `test_diagnostics.py`, `test_metrics.py` (AC-E1 item 5 cases), `test_groundtruth.py` (gating, versions, seeding flag, import/export, sha mismatch), `test_comparison.py` (identical pages and GT versions enforced; `IncomparableRunsError`; staleness re-scores all runs; tag/producer breakdowns; E2 candidates), `test_errors.py` (hand-built cases: substituted letter, missing diacritic, `٢٠٢٥`→`۲۰۲٥` as `digit_form`, `٢٠٢٥`→`٥٢٠٢` as `transpose_suspect`, reversed word, inserted Latin, number check list statuses), `test_raw_vs_cleaned.py` (variant results reference the same raw run; raw text unchanged byte-for-byte after variants are computed), `test_report.py` (separate sections, opt-in content, bundle roundtrip), `test_secrets.py` (sentinel key never on disk or in logs/exports), `test_no_src_changes.py` (asserts that `lab` does not import `src` and `lab.core` does not import streamlit, by scanning AST imports).
Optional `tests/lab/test_live_fileparser.py` (`live`): one `cloudflare-ai` run on a 1-page fixture.

## 7. Commands to run and report verbatim (in `CODEX_REPORT.md`)
```bash
cd "Project sdaia"
python -m pip install -r lab/requirements-lab.txt
ruff check lab tests/lab
pytest tests/lab --cov=lab.core --cov-report=term-missing
python -m lab.fixtures.generate_fixtures
python -m lab.core.bench --fixtures lab/fixtures/generated --out lab_exports/e1_fixture_bench   # headless: runs all local adapters × variants on all fixtures, writes the report
git diff planning/multimodal-rag --stat -- src   # must be empty
python -m src.main                     # only if a key is available; otherwise "not run"
pytest tests/lab -m live               # only if a key is available; otherwise "not run"
```
`lab/core/bench.py` is a small headless CLI that reuses runner + metrics + report, so the fixture results in AC-E1 item 7 are reproducible without the UI. **Include the generated `report.md` from the fixture bench in the PR** (as `docs/architecture/E1_FIXTURE_BENCH.md`). It is evidence for review, not a verdict.

## 8. Deliverables
1. Code + tests as above, on branch `phase-e1-extraction-lab`, pushed to `origin`. After E1-A, open a **draft** PR `phase-e1-extraction-lab → planning/multimodal-rag` and keep it updated per checkpoint. Do not merge it, and never target `main`.
2. One report per checkpoint: `docs/handoff/CODEX_REPORT_E1-A.md` … `CODEX_REPORT_E1-D.md`, copied from the `CODEX_REPORT.md` template (leave the template unchanged). Each includes every AC-E1 item assigned to that checkpoint with evidence, the design deviations, the facts verified that day (library versions installed; from E1-D, the carrier model ID and price and the file-parser response shape), and anything not run and why.
3. `docs/architecture/E1_FIXTURE_BENCH.md` (generated).
4. `lab/README.md`: install, run, data handling (temporary workspace, what leaves the machine and when), cost warning, how to add an adapter.

## 9. Checkpoints (implementation milestones, **not** a reduction of scope)
All 21 AC-E1 items remain mandatory for E1 completion. Checkpoints only set the order of work and the review gates.

### Rules for every checkpoint
1. Work only on that checkpoint's scope. Don't start the next one until Claude records approval in `docs/reviews/CLAUDE_REVIEW.md` and the user relays it.
2. At the end of the checkpoint: `ruff check lab tests/lab` clean; `pytest tests/lab` green offline. **No `skip`/`xfail` that hides unimplemented work**: tests for later checkpoints simply don't exist yet. Coverage ≥ 85% on the `lab/core` modules created so far. `git diff planning/multimodal-rag --stat -- "Project sdaia/src"` is empty.
3. Leave the lab runnable: `streamlit run lab/app/Home.py` starts, and pages for later checkpoints show "available in E1-X".
4. Commit with clear messages, push the branch, and write `docs/handoff/CODEX_REPORT_E1-<X>.md`. Report **actual** changes, verbatim command output summaries, failures, and limitations. State what you did not verify. Don't claim AC items that belong to later checkpoints.
5. Stop and wait for review.

### Library verification (all checkpoints, starting in E1-A)
Install into a fresh virtual environment, then record in the report: Python version, OS, and the exact installed version of every package in `requirements-lab.txt` (`pip freeze` excerpt). Confirm each API used against the installed version (e.g. pypdfium2 text-page methods, PyMuPDF `insert_htmlbox`/`get_text` options, pdfplumber `extract_text` params, pypdf `extraction_mode`, Streamlit APIs used), and note any incompatibility. **PyMuPDF licensing stays unresolved until the production-selection phase (E5).** Don't treat its use in the Lab as a production decision, and don't add licence-driven workarounds.

### E1-A — Lab foundation, upload, PDF rendering, local text extractors
- **Build:** `requirements-lab.txt`, `.streamlit/config.toml`, `.gitignore` additions; `config/lab.toml`, `config/adapters.toml` (local adapters + the file-parser entry with `enabled=false`); `core/settings.py`; `core/models.py` (**all** LAB §4 contracts defined now, so later checkpoints don't change them); `core/workspace.py`; `core/ingest.py` (including the PDF producer/creator capture and the page-tag storage API); `core/adapters/{base,registry}.py`; the 4 local text adapters; `core/runner.py` (child processes, timeouts, timing, cache, re-run, repeat ×N); `fixtures/generate_fixtures.py` + font + licence; `tests/lab/data/` tiny PDFs; a minimal UI with Home (workspace), Documents (upload, list, delete, page viewer, producer display), Run (select adapters/pages, run, progress) and Compare **raw only** (page image beside one column per run, block-order overlay); `core/bench.py` producing run results and timing only (metrics come in E1-B).
- **AC-E1 items verified at E1-A:** 1, 2, 3; 4 (for modules built so far); 6; 7 (runs and statuses for every fixture; metrics part in E1-B); 12 (workspace end, TTL, path safety; the export part in E1-D); 13; 14 (versions, params, sha256, environment, cache hit, re-run; the bundle part in E1-D); 15a; 15c (page image + overlay; diff in E1-B).
- **Tests:** `test_models`, `test_workspace`, `test_ingest`, `test_adapters_local`, `test_runner`, `test_no_src_changes`.

### E1-B — Raw/cleaned comparison, ground truth, accuracy metrics
- **Build:** `core/adapters/postprocess.py` (4 variants, versioned, computed from stored raw); `core/groundtruth.py`; `core/metrics.py`; `core/review.py`; UI: RAW/CLEANED panes, word diff vs GT and vs another run, Ground Truth page (editor, seed, verify, import/export of GT JSON/txt), human-review form; bench adds metrics.
- **AC-E1 items:** 5; 7 (metrics part); 8; 9; 15b; 15c (diff); 15d; 15e; 17.
- **Tests:** `test_postprocess` (incl. the probe regression case), `test_raw_vs_cleaned`, `test_groundtruth`, `test_metrics`.

### E1-C — Error inspection, diagnostics, comparison sets
- **Build:** `core/diagnostics.py`; `core/comparison.py` (sets, frozen GT versions, staleness, `IncomparableRunsError`, tag/producer breakdowns, E2 candidates); `core/errors.py`; UI: comparison-set header on Compare/Errors/Results, Errors page, page-tag editor, diagnostics badges.
- **AC-E1 items:** 7 (the "no text layer" diagnostic); 18; 19 (capture, tagging, breakdowns, tests); 20 (E2 candidates, stored sets reusable by E2); 21.
- **Tests:** `test_diagnostics`, `test_comparison`, `test_errors`.

### E1-D — Reporting, exports, security, final validation (revised 2026-11-16: **OpenRouter PDF parser removed**)
- **User decision (2026-11-16):** the OpenRouter file-parser adapter is **removed from E1** under the self-hosted-only policy (SELF_HOSTED_MODEL_SELECTION.md). Don't build `core/openrouter.py`, `adapters/text_openrouter_fileparser.py`, `core/costs.py`, the API toggle, the confirmation dialog or the spend guards. The E1 lab makes **no network calls at all**.
- **Build:** `core/report.py` (all exports, bundle import); Results & Export page; `lab/README.md`; root README section; final bench → `docs/architecture/E1_FIXTURE_BENCH.md`; full-coverage pass. Remove any remaining OpenRouter entries from `adapters.toml`, `lab.toml` and `settings.py`, and the "API key configured" line on Home.
- **AC-E1 items:** 4 (all of `lab/core`); 10 (revised: no network); 11 (revised: secrets); 12 (exports); 14 (bundle round-trip); 15f; 15g; 20 (fixed scope statement, banned-claims test). **15h and 16 are superseded** by the self-hosted-only policy and aren't required.
- **Tests:** `test_report`, `test_secrets`, `test_no_network` (a socket guard fails the test on any outbound connection during a full fixture bench and a UI page run).

### Final manual evaluation (after E1-D, by the user with Claude)
Implementation and checkpoint reviews use the reproducible fixtures only. **Don't wait for real Arabic PDFs.** The user uploads real Arabic documents for the final walkthrough: AC-E1.15 on real documents, and the real-document parts of AC-E1.19 (multi-column Arabic PDF, ≥ 2 producers). E1 is complete only after this walkthrough.

## 10. Explicitly out of scope
Declaring any extractor, OCR solution or pipeline the winner (LAB §11a); structure scoring (heading/paragraph detection); OCR/VLM adapters, NAMAA/Paddle local models, table/chart tasks, Docling, pymupdf4llm, any FastAPI or `src/` change, authentication, multi-user deployment, production frontend, RAG, embeddings.
