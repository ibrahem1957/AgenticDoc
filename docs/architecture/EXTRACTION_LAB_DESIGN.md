# AgenticDoc Extraction Lab — Design

**Author:** Claude · **Date:** 2026-11-16 · **Status:** Approved design for Phase E1; E2–E4 sections are extension points only.
**Why this exists:** The strategy changed to evaluation first (see IMPLEMENTATION_PLAN §0). Before choosing the production extraction pipeline, the user wants to test extraction tools and models on their own Arabic and English documents. The Lab is a **local evaluation tool, not the product frontend**. Nothing in it is required by `src/`, and `src/` keeps working unchanged.

---

## 1. Principles

1. **Measure, don't assume.** Every number shown has a stated source. *Automatic metrics* are computed against **verified** ground truth only. *Diagnostics* are signals computed without ground truth, such as presentation-form glyph counts or empty pages. *Human review* is the user's judgement. The three are stored, shown and exported **separately** and are never merged into one score.
2. **No external call without a clear user action.** Local adapters run freely. An API adapter runs only after the user has (a) enabled external APIs for the workspace, (b) selected the adapter, and (c) confirmed a dialog that names the file, page count, provider/engine and estimated cost. The confirmation applies to one run only.
3. **Temporary by default.** Uploads, renders, outputs and ground truth live in a workspace under the OS temp dir and are deleted when the workspace ends, at startup after a TTL, or on request. To keep anything, the user exports a bundle and can import it later.
4. **No winner is hard-coded.** Adapters and models are listed in a config file and chosen in the UI. Defaults only decide which adapters are pre-ticked.
5. **Page-faithful.** Results are stored per page in the order the tool produced them. The Lab never reorders or "fixes" output silently. Post-processing such as Arabic normalization is an explicit, separately labelled **variant**.
6. **Extensible by task.** Tasks `text`, `ocr`, `table` and `chart` share the workspace, runner, storage, cost tracking and report machinery. E1 implements `text` only. The other tasks are registered as "coming in E2–E4" and add their own adapters, ground-truth schemas and metrics.
7. **CPU only.** No adapter in E1 needs a GPU. Local-GPU models (e.g. NAMAA Qari-OCR, PaddleOCR-VL) are E2 candidates behind an optional adapter that is disabled unless its dependencies are present.

## 2. Location and structure

The Lab lives in its own package beside `src/`, so it cannot break the existing app:

```
Project sdaia/
  src/                      # existing app — untouched in E1
  lab/
    __init__.py
    README.md               # how to install/run, data handling, cost warning
    requirements-lab.txt    # separate dependency set
    config/
      adapters.toml         # adapter registry: enabled, defaults, params, model IDs, prices
      lab.toml              # limits, TTL, render DPI, timeouts
    core/                   # NO streamlit imports here (testable, reusable in E5)
      settings.py           # loads lab.toml + env (OPENROUTER_API_KEY only via env/.env)
      models.py             # Pydantic data contracts (§4)
      workspace.py          # temp workspace lifecycle, safe paths, sweeper
      ingest.py             # upload validation, sha256, page count, page rendering
      adapters/
        base.py             # Adapter protocol, AdapterInfo, capability flags
        registry.py         # loads adapters.toml, checks deps/availability
        text_pymupdf.py
        text_pypdfium2.py
        text_pdfplumber.py
        text_pypdf.py
        text_openrouter_fileparser.py   # API, off by default
        postprocess.py      # variants: arabic presentation-form folding, whitespace
      runner.py             # isolated subprocess execution, timeouts, timing, caching
      diagnostics.py        # ground-truth-free signals
      metrics.py            # CER/WER etc. (only with verified GT)
      comparison.py         # ComparisonSet building, freezing, staleness, re-scoring (§8.1)
      errors.py             # alignment → ErrorItem, categories, number check list (§8.2)
      groundtruth.py        # GT storage, seeding, verification state, versions
      review.py             # human review records
      costs.py              # usage ledger, cost estimation, OpenRouter catalog check
      report.py             # JSON / CSV / Markdown / ZIP export + import
    app/
      Home.py               # Streamlit entry (streamlit run lab/app/Home.py)
      pages/1_Documents.py
      pages/2_Run_Text_Extraction.py
      pages/3_Compare.py
      pages/4_Ground_Truth.py
      pages/5_Errors.py
      pages/6_Results_and_Export.py
      components.py         # RTL-aware text panes, diff rendering, page viewer
    fixtures/
      generate_fixtures.py  # synthetic PDFs + exact ground truth
      fonts/                # OFL Arabic font + LICENSE (e.g. Noto Naskh Arabic or Amiri)
      README.md
  tests/lab/                # pytest, offline
```

Dependency rule: `lab.core` must not import `streamlit`, and `src` must not import `lab`. In E1, `lab` does **not** import from `src` either. It has its own small OpenRouter client, so it doesn't depend on code scheduled for refactoring. E5 merges the validated pieces into `src`.

## 3. Workspace lifecycle (temporary storage)

| Aspect | Rule |
|---|---|
| Root | `LAB_TMP_DIR` (default `<tempfile.gettempdir()>/agenticdoc-lab`) |
| Workspace | One per Streamlit browser session: `ws_<token_urlsafe(16)>`, stored in `st.session_state`. "New workspace" and "End workspace (delete everything)" buttons. |
| Layout | `ws_x/workspace.json`, `docs/<doc_id>/original.<ext>`, `docs/<doc_id>/pages/p0001.png`, `runs/<run_id>/result.json`, `gt/<doc_id>.json`, `reviews/<run_id>.json`, `ledger.jsonl` |
| TTL | Workspaces untouched for `workspace_ttl_hours` (default 24) are deleted by a sweep on app start and every 30 min |
| Paths | All disk paths come from generated IDs. User filenames are kept for display only, after sanitizing. Every path is checked with `resolve().is_relative_to(root)`. |
| Limits | File ≤ 50 MB, ≤ 200 pages (E1), ≤ 30 documents per workspace (configurable) |
| Accepted inputs | PDF (magic `%PDF-`) and images (PNG/JPEG/TIFF/WebP by magic bytes). Images are stored and viewable in E1. The `text` task reports them as *not applicable — needs OCR (E2)*. |
| Persistence across restarts | Workspaces on disk survive a crash until the TTL sweep, so the user can re-attach to the latest workspace from the Home page. They are never moved elsewhere. |
| Third-party data | Content sent to OpenRouter is outside local deletion. The Lab shows this statement in the API confirmation dialog. |

## 4. Data contracts (`lab/core/models.py`)

```python
class LabDocument(BaseModel):
    doc_id: str; display_name: str; kind: Literal["pdf", "image"]
    sha256: str; size_bytes: int; page_count: int
    page_sizes: list[tuple[float, float]]            # points
    has_text_layer: list[bool] | None                 # per page, from a cheap probe
    pdf_producer: str | None; pdf_creator: str | None # from the PDF Info dict, verbatim (real-document producer tracking)
    page_tags: dict[int, list[PageTag]]               # user-assigned, see below
    uploaded_at: datetime

PageTag = Literal["multi_column", "headings", "diacritics", "arabic_indic_digits", "western_digits",
                  "mixed_ar_en", "header_footer", "footnotes", "tables_present", "images_present",
                  "low_quality", "other"]

class ComparisonSet(BaseModel):          # the unit of comparison (§8.1)
    set_id: str; doc_id: str; doc_sha256: str
    pages: list[int]                     # identical for every run in the set
    gt_versions: dict[int, int]          # page → verified GT version used; frozen when the set is scored
    run_ids: list[str]                   # each run covers exactly `pages`
    page_set_hash: str                   # sha256 of doc_sha256 + sorted pages + gt_versions

class ErrorItem(BaseModel):              # one aligned difference (§8.2)
    run_id: str; variant: str; page: int; index: int
    op: Literal["substitute", "insert", "delete", "transpose_suspect"]
    ref: str; hyp: str                   # the differing span (may be empty)
    ref_context: str; hyp_context: str   # ±30 chars around the span
    ref_offset: int; hyp_offset: int
    categories: list[Literal["digit", "digit_form", "diacritic", "arabic_letter", "presentation_form",
                             "ligature", "latin", "punctuation", "whitespace", "order"]]

class AdapterInfo(BaseModel):
    adapter_id: str                 # e.g. "text.pymupdf"
    task: Literal["text", "ocr", "table", "chart"]
    label: str; kind: Literal["local", "api"]
    library: str; library_version: str | None; license: str
    model_id: str | None            # API adapters
    params: dict                    # effective params (part of the cache key)
    available: bool; unavailable_reason: str | None
    supports_blocks: bool           # returns blocks with bboxes (for order overlay)

class TextBlock(BaseModel):
    order: int; text: str
    bbox: tuple[float, float, float, float] | None    # points, top-left origin

class PageResult(BaseModel):
    page: int                        # 1-based
    text: str                        # exactly as produced (after the variant's post-processing)
    blocks: list[TextBlock] | None
    status: Literal["ok", "empty", "error", "not_applicable"]
    error: str | None
    elapsed_ms: float | None         # when the tool works per page

class RunResult(BaseModel):
    run_id: str; doc_id: str; doc_sha256: str
    adapter: AdapterInfo
    variant: str                     # "raw" | "arabic_fold" | ...
    pages: list[PageResult]
    page_mapping: Literal["exact", "approximate", "document_only"]   # see §5.5
    started_at: datetime
    wall_ms: float; cpu_ms: float | None
    usage: UsageRecord | None        # API only
    status: Literal["ok", "partial", "error", "timeout", "cancelled"]
    error: str | None
    cache_hit: bool
    environment: dict                # python, platform, lab version

class GroundTruthPage(BaseModel):
    page: int; text: str
    status: Literal["draft", "verified"]
    seeded_from: str | None          # adapter_id/variant if seeded from an output; None if typed/imported
    verified_by: str | None; verified_at: datetime | None
    notes: str | None

class GroundTruth(BaseModel):
    doc_id: str; doc_sha256: str; task: Literal["text"]
    pages: list[GroundTruthPage]; version: int     # +1 on each save; history kept in-file
    source: Literal["manual", "fixture", "imported"]

class MetricResult(BaseModel):
    run_id: str; page: int | None    # None = document aggregate
    gt_version: int
    cer: float; wer: float; cer_no_diacritics: float
    bow_f1: float                    # order-insensitive word F1
    num_recall: float | None; num_precision: float | None
    ref_chars: int; hyp_chars: int

class Diagnostics(BaseModel):
    run_id: str; page: int
    chars: int; arabic_ratio: float; latin_ratio: float
    presentation_forms: int; replacement_chars: int; cid_tokens: int
    private_use_chars: int; empty: bool
    arabic_ligatures: int                     # U+FDF0–U+FDFD (e.g. ﷲ ﷼)
    digits_arabic_indic: int; digits_extended: int; digits_ascii: int
    diacritics_detached: int                  # diacritic preceded by whitespace
    suspected_reversed_arabic: float | None   # heuristic share, labelled as a hint

class HumanReview(BaseModel):
    run_id: str; page: int | None
    rating: Literal["correct", "minor_issues", "major_issues", "unusable"]
    issues: list[Literal["reversed_order", "wrong_column_order", "broken_letters",
                         "missing_text", "extra_text", "numbers_changed", "diacritics_lost",
                         "header_footer_noise", "merged_words", "split_words", "other"]]
    notes: str | None; reviewer: str | None; created_at: datetime

class UsageRecord(BaseModel):
    provider: str; model: str | None; engine: str | None
    prompt_tokens: int | None; completion_tokens: int | None; pages_billed: int | None
    cost_usd: float | None; cost_source: Literal["response", "estimated", "unknown"]
    latency_ms: float; request_count: int; retries: int
```

All files carry `"schema_version": 1`.

## 5. E1 text extraction adapters

### 5.1 Adapter protocol
```python
class Adapter(Protocol):
    info: AdapterInfo
    def check_available(self) -> tuple[bool, str | None]: ...      # deps import, key present, model in catalog
    def estimate_cost(self, doc: LabDocument, pages: list[int]) -> CostEstimate: ...  # 0 for local
    def run(self, pdf_path: Path, pages: list[int], params: dict, ctx: RunContext) -> list[PageResult]: ...
```
Adding an adapter means one module plus an `adapters.toml` entry. There are no UI changes, because the UI is generated from the registry.

### 5.2 E1 adapter set

| adapter_id | Kind | Library (licence) | What is extracted | Blocks/bboxes | Notes |
|---|---|---|---|---|---|
| `text.pymupdf` | local | PyMuPDF (AGPL-3.0) | `page.get_text("text")`. Param `sort` (bool) is reported as a separate configuration. | yes (`"dict"` / `"blocks"`) | Partly logical-order output; best and worst probe results depending on producer (§7) |
| `text.pypdfium2` | local | pypdfium2 (Apache-2.0/BSD) | `textpage.get_text_range()` | yes (per-char boxes, grouped into lines by the adapter only for the overlay) | Folds presentation forms to base letters itself; mixed order (§7) |
| `text.pdfplumber` | local | pdfplumber / pdfminer.six (MIT) | `page.extract_text()`. Params `layout` and `x_tolerance` | yes (words) | Known RTL weaknesses; included as a contrast baseline |
| `text.pypdf` | local | pypdf (BSD-3) | `page.extract_text()`, param `extraction_mode` ∈ {plain, layout} | no | Pure Python |
| `text.openrouter_fileparser` | **api** | OpenRouter `file-parser` plugin | Parsed content from `annotations[].file.content[]` text parts. Engines `cloudflare-ai` (free) and `mistral-ocr` ($2 / 1k pages) | no | Off by default. The documented output is **not split per page** (§5.5). Uses a small carrier chat model; see §6. |

Post-processing **variants**, selectable per run and applicable to any adapter's output. Each variant is stored as its own result and computed from the stored `raw` output, so it needs no re-extraction:
- `raw`: always produced.
- `arabic_fold`: NFKC applied only to code points in U+FB50–U+FDFF and U+FE70–U+FEFF (presentation forms and Arabic ligatures, e.g. `ﷲ` → `الله`). Tatweel removal is an opt-in param. Diacritics and digits are never changed. Note that NFKC turns `﷼` into `ریال` with Farsi yeh U+06CC. This is recorded as a known effect, not "fixed".
- `bidi_reorder`: per line, applies the Unicode bidi algorithm (python-bidi `get_display`, base direction RTL when the line is Arabic-dominant), turning visual-order lines into logical order. It **helps some extractors and hurts others** (§7), so it is a measured variant, never a default.
- `bidi_reorder+arabic_fold`: both, in that order.

Variant definitions are versioned (`variant_version`) and part of the cache key.

**Deferred to later phases (explicitly not in E1):** `pymupdf4llm` Markdown (layout/tables, E3), Docling (model downloads, tables, E3), any VLM/OCR model (E2), NAMAA Qari-OCR / PaddleOCR-VL local adapters (E2, optional GPU).

### 5.3 Runner (`runner.py`)
- Each local adapter runs in a **child process** (`multiprocessing` spawn context, Windows-safe) with a per-document timeout (default 120 s) and a page cap. This protects the UI from hangs and crashes on malformed PDFs.
- Timing: `wall_ms` is measured **inside** the child around the extraction call only, excluding process start and imports. `cpu_ms` comes from `time.process_time()` in the child. Per-page `elapsed_ms` is recorded where the loop is per page. The UI shows the median of N repeats when the user selects "repeat ×3" (local adapters only).
- **Cache:** key = `sha256(doc) + adapter_id + library_version + model_id + canonical(params) + variant + pages`. A cache hit returns the stored result with `cache_hit=true`. API results are cached the same way. "Re-run" bypasses the cache explicitly and needs a new confirmation for API adapters.
- Adapters on the same document run sequentially by default. There is no parallel API fan-out in E1.

### 5.4 Page rendering for the viewer
`ingest.py` renders pages to PNG with pypdfium2 at 110 DPI for the viewer, lazily per page, cached in `pages/`. If the run being viewed has blocks with bboxes, the viewer can draw **numbered block boxes** over the page. This makes reading order (RTL, columns) visible without ground truth.

### 5.5 Page mapping for document-level outputs
If an adapter returns only document-level text (the file-parser), the Lab first checks for explicit page delimiters in the returned parts. If it finds none, it stores the text as page `0` with `page_mapping="document_only"`. Metrics for such a run are then **document-level only**, against the concatenated verified pages. The UI labels this result "no page mapping". Text is never split heuristically into pages and then presented as exact.

## 6. OpenRouter usage in the Lab
- **Key:** read from the `OPENROUTER_API_KEY` env var or `.env`. Never written to the workspace, logs, exports or the UI. The UI only shows "API key configured: yes/no".
- **Availability check** (`costs.py`): when the user ticks an API adapter, the Lab fetches `GET /api/v1/models` (public, cached 1 h). If the configured carrier model ID isn't listed, the adapter shows as unavailable with the reason. File-parser engines can't be verified from the catalog. They are marked "unverified" until the first successful run and verified afterwards; the state is kept per workspace.
- **Carrier model:** the file-parser needs a chat completion. The default is the cheapest suitable text model chosen in config, with an instruction to reply "OK" and `max_tokens` small. The Lab uses only the `annotations` content, not the model's answer. Codex must confirm with one live call that the annotations contain the parsed text. If they don't, the adapter ships disabled and the finding is reported.
- **Privacy:** request body includes `provider: {data_collection: "deny"}` (+ `zdr: true` if `require_zdr` is set in `lab.toml`).
- **Confirmation dialog** shows: file name, pages to send, engine, carrier model, estimated cost (`mistral-ocr`: pages × $0.002 + carrier tokens; `cloudflare-ai`: carrier tokens only), and the third-party retention statement. The user must check "I understand this file will be sent to OpenRouter" and press Run.
- **Spend guard:** `max_cost_per_run_usd` (default 0.50) and `max_cost_per_workspace_usd` (default 2.00) in `lab.toml`. A run whose estimate exceeds either limit is blocked.
- **HTTP:** connect timeout 10 s, read timeout 180 s, at most 2 retries on 429/5xx with `Retry-After`. Errors are shown with status code and provider message, never with headers or the key.
- **Usage:** read `usage` (tokens, and cost if present) from the response; otherwise estimate from `adapters.toml` prices. `cost_source` is always shown.

## 7. Feasibility probe (run by Claude, 2026-11-16, scratch venv)

**Setup:** one Arabic/English sentence with diacritics, Arabic-Indic and Western numbers, `٫`, `٪`, `ريال` and `الله`. The PDF was generated by PyMuPDF 2.1 `insert_htmlbox` (`dir="rtl"`) with 4 Windows fonts, and by Microsoft Edge (Chromium) headless `--print-to-pdf`. It was then extracted with PyMuPDF 2.1, pypdfium2 5.15.2, pdfplumber 0.11.10 and pypdf 7.1.0. CER is measured against the source sentence (whitespace collapsed). Scripts: `docs/architecture/evidence/e1_probe/`. **This is a tiny probe (one sentence, one line wrap), not a benchmark.** It is here to shape the design, not to rank tools.

| Producer / font | PyMuPDF | pypdfium2 | pdfplumber | pypdf |
|---|---|---|---|---|
| PyMuPDF / Arial | 0.644 (0.269 after NFKC) | 0.615 | 0.894 | 0.654 |
| PyMuPDF / Tahoma | 0.644 (0.269) | 0.663 | 0.827 | 0.654 |
| PyMuPDF / Times | 0.654 (0.298) | 0.606 | 0.894 | 0.654 |
| PyMuPDF / Segoe UI | 0.615 (**0.067**) | 0.538 | 0.808 | 0.760 |
| Edge (Chromium) / Arial | 0.894 | **0.269** | 0.894 (0.135 after bidi + NFKC) | 0.904 |

Variant effect (CER raw → bidi visual-to-logical reorder → + NFKC):
- pdfplumber: Arial 0.894 → 0.644 → **0.154**; Edge 0.894 → 0.433 → **0.135**.
- pypdfium2: Edge 0.269 → 0.894; Arial 0.615 → 0.885. Reordering **hurts** it.

**Observed failure modes:** presentation-form glyphs in the text layer (U+FExx, up to 54 per sentence); ligature code points (`ريال` → `﷼` U+FDFC, `الله` → `ﷲ` U+FDF2); Arabic-Indic digits turned into Extended Arabic-Indic digits by shared font glyphs (`٢٠` → `۲۰`); digits reversed within RTL runs (`٢٠٢٥` → `٥٢٠٢`); whole lines reversed (visual order); letters reversed within words; diacritics split from their letters by spaces; line order swapped after wrapping.

**Design consequences (applied in this document and the E1 task):**
1. **Native text is not automatically exact.** Errors come from both the PDF producer's encoding and the extractor's RTL handling. This contradicts the earlier assumption in MODEL_RESEARCH §2.5 item 1, which is now corrected. It also makes E1 essential before E5 decides between native extraction and OCR routing.
2. **Ground truth is the visible text**, what a reader sees on the page. It is not whatever the text layer encodes. Encoding losses therefore count as errors, which is correct for deciding when OCR (E2) should replace the text layer.
3. **Fixtures can't be assumed to round-trip.** They are generated with several producers and fonts, and the producer and font are recorded. They are good for regression and coverage, but conclusions need the user's real documents.
4. **Post-processing must be measured per extractor, never applied globally.** E1 ships composable variants: `raw`, `arabic_fold` (NFKC on presentation forms and Arabic ligatures), `bidi_reorder` (python-bidi, per line, base direction RTL for Arabic-dominant lines), and `bidi_reorder+arabic_fold`.
5. **Diagnostics** add counts of presentation forms, Arabic ligature code points (U+FDF0–U+FDFD), and digit forms by script (U+0660–0669 vs U+06F0–06F9 vs ASCII).

## 8. Metrics (`metrics.py`) — only with verified ground truth

| Metric | Definition | Purpose |
|---|---|---|
| CER | char Levenshtein / ref chars, after NFC + whitespace collapse; diacritics kept | Main accuracy |
| WER | token Levenshtein / ref tokens (whitespace tokenization after NFC) | Word-level accuracy |
| CER (no diacritics) | CER after removing U+064B–U+065F, U+0670 from both sides | Shows the diacritics-only share of the error |
| Bag-of-words F1 | multiset token overlap F1 | Order-insensitive. **High BoW F1 with high CER/WER means an ordering problem, not missing content.** |
| Numeric recall / precision | number tokens (Western, Arabic-Indic U+0660–0669, Extended U+06F0–06F9, separators `. , ٫ ٬`, `% ٪`) must match **exactly**, with no digit-form conversion | Number fidelity. Low precision suggests altered or hallucinated numbers. |

### 8.1 Comparability rules: same pages, same reference
- Metrics are comparable across extractors **only inside a `ComparisonSet`**. Every run in a set covers exactly the same document (sha256) and page list, and is scored against the same frozen GT version per page. The runner builds sets automatically when the user runs several adapters/variants on one page selection.
- A ranking or side-by-side metric table is shown only for one `ComparisonSet` at a time. Runs on different page sets or GT versions are never placed in the same table. The UI offers "re-run on the missing pages" instead.
- If GT changes after scoring, the set is marked **stale**, and every run in it is re-scored against the new versions together, never one run at a time.
- Each metric row carries `set_id` and `page_set_hash`. Exports keep them.
- A page enters a set's metrics only when it is verified, and then for **all** runs in the set at once.

### 8.2 Error inspection (individual errors, not only aggregates)
- For each (run, variant, verified page), the Lab computes the character-level alignment (`rapidfuzz.distance.Levenshtein.opcodes`), merges adjacent operations into spans, and emits `ErrorItem`s with context and categories. Categories are assigned by Unicode class; `digit_form` = same numeric value in a different script, e.g. `٢`↔`۲`↔`2`. `transpose_suspect` marks a span whose reversal equals the reference span, which catches reversed words and numbers.
- The **Errors view** lists errors for one page and one or more runs. It filters by category and op, sorts by position, and highlights the span in both texts when an error is selected. It also shows per-category counts, plus a **number check list**: every reference number with found / missing / altered (and in which form), and every output number absent from the reference.
- `errors.csv` is part of the export.

### 8.3 Verified-GT gating
- Pages whose GT is `draft` produce **no metrics**. The UI shows "verify ground truth to compute accuracy".
- Document aggregates are micro-averaged (sum of edits / sum of ref lengths) over verified pages only, with "verified pages: k / n" shown next to every aggregate.
- Each metric row stores `gt_version`. Editing GT marks earlier metrics stale and they are recomputed on view.
- Implementation: `rapidfuzz` (MIT) `Levenshtein.distance`, which works on strings and on token lists. Hand-computed unit tests are required.

## 9. Ground truth workflow
1. **Sources:** (a) typed or pasted manually per page, (b) imported from a `.txt` (pages split by form-feed `\f`) or a Lab GT JSON, (c) seeded from a run's output and then edited, (d) generated with the fixtures (`source="fixture"`, auto-verified because it is exact by construction).
2. **Seeding warning:** seeding from adapter X records `seeded_from=X`. Metrics tables flag X's scores on those pages with "GT seeded from this adapter — may be biased". The UI recommends seeding from the output the user judges best only after side-by-side review.
3. **Verification:** per-page "Mark verified" checkbox with optional reviewer name. Verified pages can be edited, which creates a new version and returns the page to `draft` until re-verified.
4. **Editor:** RTL-aware text area (`dir="auto"`), the page image beside it, and a live diff against the selected run.

## 10. UI (Streamlit, minimal)

| Page | Contents |
|---|---|
| Home | Workspace ID, created/TTL, New/End workspace, re-attach to recent workspace, API key status, "Allow external API calls in this workspace" toggle (default off), spend so far |
| Documents | Upload (multi-file), table of documents (name, type, pages, size, text-layer pages k/n), delete document, page viewer |
| Run Text Extraction | Choose document(s) + page range; tick adapters (local ones pre-ticked from config, API ones off); choose variants; repeat ×N; "Estimate" and "Run"; API confirmation dialog; progress and per-adapter status |
| Compare | Comparison-set and page selector; original page image on the left; one column per selected run. In each column **raw text and the selected cleaned variant are shown separately, stacked and labelled** (`RAW — exactly as extracted` / `CLEANED — <variant> v<version>`), never merged, and raw can't be hidden while a variant is shown. RTL-aware, monospace toggle, show-invisible-characters toggle; optional block-order overlay; diff mode vs GT or vs another run (word-level, colored insert/delete, `dir="rtl"` for Arabic); diagnostics badges per column; human-review form per run/page |
| Errors | §8.2: error list with filters, span highlighting in both texts, per-category counts, number check list |
| Ground Truth | Per-page editor (§9), import/export GT, verification status |
| Results & Export | Three separate tables: **Automatic metrics** (verified GT only), **Diagnostics**, **Human review**; timing and cost table; export buttons |

Rendering: all user and extracted text is escaped before HTML rendering. `unsafe_allow_html` is used only with Lab-generated markup around escaped text.

## 11. Export / import (`report.py`)
- `results.json` (all runs, metrics, diagnostics, reviews, usage, environment, schema_version)
- `metrics.csv` (with `set_id`, `page_set_hash`), `errors.csv`, `timing_cost.csv`, `reviews.csv`
- `report.md`: method, documents (name, sha256, pages, PDF producer/creator, page tags), adapters with versions and params, one section per `ComparisonSet`, the three tables kept separate, breakdowns by page tag and producer, the list of E2 candidate pages, the fixed scope statement from §11a, a limitations section, and how many pages were verified
- `bundle.zip` = all of the above + GT JSON. Original documents and extracted texts are **excluded by default**, each behind its own checkbox, because they may be confidential.
- Import of `bundle.zip`/GT JSON restores GT, reviews and results. GT is matched to documents by `sha256`, and the import is refused when the hash differs.

## 11a. What E1 may and may not conclude
- E1 measures **text-layer extraction only**. It can say which extractor/variant reproduces the visible text best **on the evaluated pages**, broken down by page tag and PDF producer, with the number of verified pages shown.
- E1 **must not** declare a winning Arabic OCR solution, or a production pipeline. `report.md` always contains this fixed statement: *"Phase E1 evaluates native PDF text layers only. It does not evaluate OCR or OpenRouter vision models (Phase E2) and is not a basis for selecting an Arabic OCR solution. Results apply only to the documents and pages listed."*
- Pages where every local extractor scores poorly, or that have no text layer, are listed in the report as **"E2 candidates"**. They become the first inputs for the OCR/VLM comparison, so E2 can run on exactly the same pages and reference text.
- Breakdowns: metrics per `page_tag` and per `pdf_producer`. A tag group with fewer than 3 verified pages is shown as "insufficient data".
- E1 evaluates heading and paragraph text and its order. It does **not** score structure, i.e. whether an element is detected as a heading or paragraph. Structure scoring is part of E3/E5 and is listed as a limitation in the report.

## 12. Extension points for E2–E4 (designed now, not built)
- `task` field everywhere. Registry entries per task. Each task module supplies `GroundTruth` subtype, metrics and a compare widget.
- **E2 OCR:** reuses E1 `ComparisonSet`s and verified GT unchanged, so OCR/VLM outputs are scored against the identical pages and reference text as the E1 extractors, in one table. Adapters for OpenRouter VLMs (page image → text, model list from config validated against `/models`), `mistral-ocr`, optional local Qari-OCR / PaddleOCR-VL. Same text metrics plus DPI / degradation variants.
- **E3 tables:** GT = cell grid; metrics = cell EM, numeric cell EM, TEDS; adapters = PyMuPDF `find_tables`, pdfplumber tables, VLM, possibly Docling.
- **E4 charts:** GT = data points with `printed | estimated` flags; metrics = printed-value EM, abstention, hallucinated-value rate.

## 13. Security
Uploads are validated by magic bytes. User input never builds a disk path. Parsing runs in child processes with timeouts. Image decompression is capped (`PIL.Image.MAX_IMAGE_PIXELS` or the pypdfium2 render-size cap). The key comes only from the environment. Logs contain IDs, timings and counts, never document text. Streamlit runs bound to `localhost` (`--server.address 127.0.0.1`), with telemetry disabled (`browser.gatherUsageStats=false`) in `lab/.streamlit/config.toml`.
