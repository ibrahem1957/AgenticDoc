> **SUPERSEDED 2026-11-16 — not implemented.** Withdrawn by the evaluation-first strategy (IMPLEMENTATION_PLAN §0). Kept for reuse in Phase E5. Do not implement.

# CODEX TASK — Phase 1: Backend Foundation

**Issued by:** Claude (architect/reviewer) · **Date:** 2026-11-16 · **Branch:** `phase-1-foundation` from `main` @ `c0a4f5a`
**Acceptance:** `docs/architecture/ACCEPTANCE_CRITERIA.md` → **AC-1** (all 13 items).
**Read first:** `docs/architecture/REPOSITORY_AUDIT.md`, `TECHNICAL_DESIGN.md` §3, §4, §8, §10, §11, §12.

## 0. Constraints
- Working directory for all commands: `Project sdaia/`. Do not rename or move it.
- Do **not** change the behavior of `BaseAgent`, `ChatBot`, prompts, chunker, vector store, or `main.py`'s flow. Those are later phases.
- Do **not** implement PDF extraction, OCR, vision, retrieval changes, chat/summary/question endpoints.
- No network in unit tests. Live tests: `@pytest.mark.live`, auto-skipped without `OPENROUTER_API_KEY`.
- Python ≥ 3.11. Type hints everywhere in new code. No new framework beyond those listed.
- If anything in this task conflicts with the code you find, stop and record it under "Design deviations" in the report rather than improvising.

## 1. Packaging & hygiene
1. `Project sdaia/pyproject.toml` (setuptools; package `src`), with extras `dev`. Also generate `requirements.txt` and `requirements-dev.txt` with pinned **minimum** versions.
   - Runtime: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `python-multipart`, `requests`, `numpy`, `python-dotenv`, `tiktoken`.
   - Dev: `pytest`, `pytest-cov`, `httpx`, `ruff`.
2. Root `.gitignore`: `__pycache__/`, `*.pyc`, `.env`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `**/eval/results/raw/` (the `**/` prefix is required because `eval/` lives under `Project sdaia/`), `*.egg-info/`, and the default temp dir if inside the repo.
3. `git rm --cached` all committed `__pycache__/*.pyc`.
4. `Project sdaia/.env.example` listing every setting from §2 with safe defaults and **no real key**.
5. `pytest.ini`/`pyproject` config: register marker `live`; default `addopts = -m "not live"`.

## 2. Configuration — `src/config.py`
`pydantic-settings` `Settings` class, env prefix `AGENTICDOC_` (except `OPENROUTER_API_KEY`), loaded once via `get_settings()` (cached; overridable in tests).

| Setting | Default |
|---|---|
| `OPENROUTER_API_KEY` | required at call time, not at import time (tests must import without it) |
| `openrouter_base_url` | `https://openrouter.ai/api/v1` |
| `app_name` / `app_url` | `AgenticDoc` / `https://github.com/ibrahem1957/AgenticDoc` (sent as `X-Title` / `HTTP-Referer`) |
| `model_chat` | `openai/gpt-4o-mini` |
| `model_embedding` | `openai/text-embedding-3-small` (unchanged in Phase 1; Phase 4 bake-off decides) |
| `model_ocr`, `model_vision_describe`, `model_vision_analyze` | `google/gemini-3.1-flash-lite`, `google/gemini-3.1-flash-lite`, `google/gemini-3.7-flash` (unused in Phase 1, defined now) |
| `model_rerank` | `qwen/qwen3-reranker-8b` (unused) |
| `provider_data_collection` | `deny` |
| `provider_require_zdr` | `false` |
| `http_connect_timeout_s` / `http_read_timeout_s` / `http_vision_read_timeout_s` | 10 / 120 / 180 |
| `http_max_retries` / `http_backoff_base_s` / `http_backoff_max_s` | 4 / 1.0 / 30 |
| `tmp_dir` | `<tempfile.gettempdir()>/agenticdoc` |
| `session_idle_ttl_s` / `session_max_ttl_s` / `sweeper_interval_s` | 3600 / 86400 / 300 |
| `max_file_bytes` / `max_txt_bytes` / `max_pdf_pages` / `max_documents_per_session` / `max_session_bytes` | 50 MB / 5 MB / 500 / 20 / 300 MB |
| `session_max_cost_usd` | 1.00 |
| `log_level` / `debug_content_logging` / `env` | `INFO` / `false` / `development` |
| `model_prices` | dict model→{prompt, completion, image} USD per token, used only when the response lacks cost; seed with the two current models' catalog prices ($0.15/M, $0.60/M; $0.02/M) |

Validation: refuse `debug_content_logging=true` when `env=production`.

## 3. OpenRouter client — `src/llm/client.py`, `errors.py`, `usage.py`
```python
class OpenRouterClient:
    def __init__(self, settings: Settings, transport: Transport | None = None, ledger: UsageLedger | None = None): ...
    def chat(self, messages: list[dict], *, model: str | None = None, temperature: float | None = None,
             max_tokens: int | None = None, response_format: dict | None = None,
             operation: str = "chat", session_id: str | None = None, trace_id: str | None = None,
             timeout_read: float | None = None) -> ChatResult      # ChatResult(text, model, usage: CallUsage, raw_id)
    def embed(self, inputs: list[str], *, model: str | None = None, operation: str = "embed",
              session_id: str | None = None, trace_id: str | None = None) -> EmbedResult  # vectors in input order
    def rerank(self, query: str, documents: list[str], *, model: str | None = None, top_n: int | None = None, ...) -> RerankResult
```
- `Transport` protocol: `post(url, headers, json, timeout) -> TransportResponse(status, headers, json|text)`. Default = `requests.Session`. Tests use `FakeTransport` (scripted responses + recorded calls) in `tests/fakes.py`.
- Headers: `Authorization: Bearer …`, `Content-Type`, `HTTP-Referer`, `X-Title`.
- Every chat/embed/rerank body includes `"provider": {"data_collection": settings.provider_data_collection}` plus `"zdr": true` when configured. **Verify against current OpenRouter docs that the embeddings and rerank endpoints accept `provider`; if not, omit it there and record that in the report.**
- Retries: on 429, 500, 502, 503, 504, 524, 529, connection errors, timeouts. Honor `Retry-After` (seconds) when present, else exponential backoff with full jitter, capped. Never retry 400/401/402/403/404/413. Inject `sleep` for tests.
- Errors (`errors.py`): `OpenRouterError` base; `AuthError` (401/403), `InsufficientCreditsError` (402), `RateLimitError`, `UpstreamError` (5xx/timeouts after retries), `InvalidRequestError` (400/404/413), `InvalidResponseError` (missing `choices`/`data`, non-JSON). Messages include status code and OpenRouter `error.message` if present; **never** the API key, headers, or request body.
- Response validation: chat requires `choices[0].message.content` (string; treat `null` as `InvalidResponseError`); embeddings require `data[*].embedding` with consistent dims, reordered by `index`.
- Missing API key → `AuthError("OPENROUTER_API_KEY is not set")` at call time.
- Embedding batching: `embed()` splits inputs into batches of ≤ 64 items, concatenates results in order.
- Usage (`usage.py`): `CallUsage(model, prompt_tokens, completion_tokens, image_count, cost_usd, cost_source: "response" | "estimated" | "unknown", latency_ms, status, operation, session_id, trace_id, timestamp)`. Read `usage.cost` from the response if present (verify the current OpenRouter usage-accounting docs; if cost requires a request flag, send it and record which flag in the report); else estimate from `model_prices`. `UsageLedger` is thread-safe; `totals(session_id)` → tokens/cost/calls; `for_session()`; `clear_session()`.

## 4. Legacy compatibility shims (behavior preserved)
- `src/llm/openrouter.py`: `OpenRouterLLM.__init__()` still raises `ValueError("OPENROUTER_API_KEY is missing")` when absent; `invoke(prompt) -> str` now calls `OpenRouterClient.chat([{"role":"user","content":prompt}])` and **still returns `f"ERROR: {e}"` on failure** (preserved on purpose until Phase 5; add a `# TODO(phase-5)` comment referencing audit D5).
- `src/rag/embeddings.py`: `OpenRouterEmbeddings.embed(text) -> list[float]` uses the client (gains timeouts/retries); add `embed_many(texts) -> list[list[float]]`. Do not change `RAGPipeline` in this phase.
- `main.py`: unchanged except it must not fail import when run from `Project sdaia/` (`load_dotenv()` before client construction — already true; leave as is).

## 5. Data contracts — `src/documents/models.py`
Implement **all** models in TECHNICAL_DESIGN §4 exactly (names, fields, enums). Add `element_id` / `chunk_id` builder helpers and JSON (de)serialization round-trip tests. Fields not populated in Phase 1 are still defined.

## 6. Validation — `src/documents/validation.py`
`validate_upload(filename: str, data_stream, declared_size: int | None, settings) -> ValidatedUpload(kind: "pdf"|"txt", mime, size, sha256, display_name)`
- Stream to a temp file inside the session dir while hashing and counting bytes; abort at `max_file_bytes` (→ `FileTooLargeError`, HTTP 413). Do not read the whole upload into memory.
- PDF: first bytes `%PDF-` (allow up to 1024 leading bytes of junk per PDF spec tolerance — document your choice). Page counting is **not** required in Phase 1 (Phase 2 adds PyMuPDF); store `page_count=None`.
- TXT: no NUL bytes in the first 8 KB; decodes as UTF-8 (BOM allowed) or UTF-16 with BOM; size ≤ `max_txt_bytes`.
- Otherwise `UnsupportedFileError` (HTTP 415).
- `display_name`: NFC, strip control/bidi-override characters (U+202A–U+202E, U+2066–U+2069), strip path components (`/`, `\`), trim to 255 chars; empty → `"document"`. Arabic filenames must survive intact (test with `تقرير المبيعات ٢٠٢٥.pdf`).

## 7. Sessions — `src/sessions/`
- `storage.py`: `SessionStorage(root)`: `session_dir(sid)`, `document_dir(sid, did)`; every path built from validated IDs (regex `^[A-Za-z0-9_-]{16,64}$`) and checked with `resolve().is_relative_to(root)`; create dirs with mode `0o700` (best effort on Windows); `delete_session`, `delete_document` idempotent; `cleanup_all()` for startup.
- `manager.py`: `SessionManager(settings, storage, clock=time.monotonic-compatible injectable, ledger)`: `create() -> SessionInfo`, `get(sid, touch=True)`, `delete(sid)`, `list_documents`, `add_document(sid, ValidatedUpload) -> DocumentRecord`, `get_document`, `delete_document`; per-session `RLock`; enforces `max_documents_per_session` and `max_session_bytes`; tombstones for expired IDs (1 h) to distinguish 410 vs 404. `session_id` = `secrets.token_urlsafe(24)`; `document_id` = `"doc_" + secrets.token_urlsafe(12)`.
- `DocumentRecord.status` = `"queued"` after upload in Phase 1 (no ingestion yet). Add a no-op `IngestionQueue` interface (`submit(sid, did)`, `cancel(sid, did)`) that Phase 2 will implement; Phase 1 implementation records the submission only.
- `sweeper.py`: background daemon thread; `run_once(now)` testable without threads; started/stopped by the FastAPI lifespan.
- On app startup: `storage.cleanup_all()` (log count of removed dirs, not names).

## 8. API — `src/api/`
- `app.py`: `create_app(settings=None) -> FastAPI` with lifespan (startup cleanup, sweeper start/stop). Run: `uvicorn src.api.app:create_app --factory`.
- Routes (TD §10): `POST /sessions`, `GET /sessions/{sid}`, `DELETE /sessions/{sid}`, `POST /sessions/{sid}/documents` (multipart field `file`), `GET /sessions/{sid}/documents`, `GET /sessions/{sid}/documents/{did}`, `DELETE /sessions/{sid}/documents/{did}`, `GET /health`.
- Responses never include absolute filesystem paths.
- Error envelope `{"error": {"code", "message", "details"?}}` via exception handlers; codes per TD §10. Unhandled exceptions → 500 with code `internal_error` and no stack trace in the body.
- `GET /sessions/{sid}` includes `usage` totals from the ledger.

## 9. Observability — `src/observability/`
- `logging.py`: JSON formatter; `get_logger(name)`; a redaction filter that masks anything matching `sk-or-[A-Za-z0-9-]+` and the configured key value.
- `tracing.py`: `new_trace_id()`, `trace_event(event: str, **fields)` that drops fields named `text`, `content`, `prompt`, `messages`, `document` unless `debug_content_logging` is true; contextvar for current `trace_id`/`session_id`.
- The client emits `llm.call` events (model, operation, status, latency_ms, tokens, cost, retries).
- Keep `observe.py` unchanged.

## 10. Evaluation scaffolding — `eval/`
- `eval/metrics.py`: `cer`, `wer`, `cer_no_diacritics`, `numeric_exact_match(ref, hyp) -> (recall, precision)`, `kendall_tau(ref_order, hyp_order)`, `table_cell_em(ref_cells, hyp_cells)`, `recall_at_k`, `mrr_at_k`. Pure Python (implement Levenshtein yourself or use a small dependency — justify it). Definitions per ACCEPTANCE_CRITERIA "Metric definitions".
- `eval/run_ocr_bakeoff.py`: CLI skeleton that loads a manifest (`eval/datasets/ocr/manifest.jsonl`: `{image_path, reference_text, tags}`), calls a list of models via `OpenRouterClient.chat` with an image message, computes metrics, writes `eval/results/ocr_<timestamp>.json` and a Markdown summary table. It must run end-to-end against `FakeTransport` in a test. No dataset is required yet.
- `tests/unit/test_metrics.py` with hand-computed cases, including: Arabic with diacritics (`مُحَمَّد` vs `محمد`), Arabic-Indic digits (`٢٠٢٥` must **not** match `2025`), decimal `٣٫٥`, percentages `٪`.

## 11. Tests (minimum)
`tests/unit/`: `test_config.py`, `test_client_chat.py`, `test_client_embed.py`, `test_client_retry.py`, `test_errors_redaction.py`, `test_usage_ledger.py`, `test_models_roundtrip.py`, `test_validation.py`, `test_storage_paths.py`, `test_session_manager.py`, `test_sweeper.py`, `test_metrics.py`, `test_legacy_shims.py`.
`tests/integration/`: `test_api_sessions.py`, `test_api_documents.py` (upload TXT/PDF happy path, 413, 415, Arabic filename, cross-session 404, delete removes dir, expired session 410, no content in logs via sentinel), `test_bakeoff_fake.py`.
`tests/live/test_openrouter_live.py` (`live`): one chat call and one embeddings call; asserts usage recorded.

## 12. Commands to run and report (verbatim summaries in CODEX_REPORT.md)
```bash
cd "Project sdaia"
python -m pip install -e ".[dev]"
ruff check src tests eval
pytest --cov=src --cov-report=term-missing
pytest -m live            # only if a key is available; otherwise state "not run"
grep -rnE "\"(openai|google|qwen|anthropic|mistralai)/" src --include=*.py
python -m src.main        # live; requires key — paste the first lines of output or state "not run"
uvicorn src.api.app:create_app --factory --port 8000  # then: curl POST /sessions, upload src/data.txt, GET documents, DELETE
```

## 13. Deliverable
Fill in `docs/handoff/CODEX_REPORT.md` (template present). Include: files added/changed, decisions and deviations, exact command outputs (pass counts, coverage table), anything not run and why, known limitations. Commit with clear messages; open a PR `phase-1-foundation → main`; do not merge. Claude reviews the PR diff and re-runs the tests independently.
