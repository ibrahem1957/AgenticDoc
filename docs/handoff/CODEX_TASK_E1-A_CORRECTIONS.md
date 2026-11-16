# CODEX TASK — E1-A Correction Round 1

**Issued by:** Claude (independent reviewer) · **Date:** 2026-11-16 · **Status:** ISSUED. Fix E1-A only, **do not start E1-B**.
**Basis:** review in `docs/reviews/CLAUDE_REVIEW.md` → Entry 7 (findings B1, M1–M5, m1–m8).
**Branch:** keep working on your existing `phase-e1-extraction-lab` with your current uncommitted E1-A work. **Don't reset, rebase or discard it.** To read this file and the updated planning docs without touching your working tree:
```bash
git fetch origin
git show origin/planning/multimodal-rag:docs/handoff/CODEX_TASK_E1-A_CORRECTIONS.md
git show origin/planning/multimodal-rag:docs/handoff/CODEX_TASK.md          # see the two "Revision 2026-11-16" notes at the top
```
Merging `origin/planning/multimodal-rag` into your branch is only needed **after** your E1-A commit (docs-only changes, which shouldn't conflict with `lab/` or `tests/`).

## 1. Blocking process item (B1)
1. Commit the E1-A work in logical commits and push `phase-e1-extraction-lab` to `origin`.
2. Open a **draft** PR `phase-e1-extraction-lab → planning/multimodal-rag` (never `main`). Don't merge it.
3. Write `docs/handoff/CODEX_REPORT_E1-A.md` from the template: actual files, verbatim command summaries (`pip install -r lab/requirements-lab.txt` in a fresh venv; `ruff check lab tests/lab`; `pytest tests/lab --cov=lab.core --cov-report=term-missing`; the fixture generation; the bench; `git diff origin/planning/multimodal-rag --stat -- "Project sdaia/src"`), `pip freeze` excerpt, Python/OS, status per assigned AC item, failures, limitations, and anything not verified.

## 2. Major fixes
- **M1 — Runner queue/join deadlock risk** (`lab/core/runner.py`, the `process.join(...)` before `output.get(...)`). Python documents that a child which has put data on a `multiprocessing.Queue` can't exit until that data is consumed. With large outputs (multi-page documents, more than the pipe buffer), `join` waits until the timeout. The run is then wrongly reported as `timeout` and the result is lost. Fix: receive the payload **before** joining (e.g. poll `output.get(timeout=…)` while the process is alive, against an overall deadline), or have the child write the result to a temp file in the workspace and send only the path. **Test:** a stub adapter returning ≥ 1 MB of Arabic text over 3 pages must finish `ok`, with intact text, well within the timeout.
- **M2 — Timing fairness:**
  - (a) `wall_ms`/`cpu_ms` in `_child_run` start **before** the adapter module import, so library import time counts as extraction time. Import the module and create the adapter first, then start the timers.
  - (b) Per-page `elapsed_ms` includes overlay-block construction: pypdfium2's per-character `_line_blocks` (quadratic in characters × lines), PyMuPDF's second `get_text("blocks")` pass, and pdfplumber's `extract_words`. This biases the timing comparison between extractors. Time **only the text-extraction call** as `elapsed_ms`/`wall_ms`, and record block construction separately (e.g. `overlay_ms` in the run's `environment` or a new optional field, documented as a design deviation).
  - **Test:** a stub whose module import sleeps 1 s must report `wall_ms` < 500 ms.
- **M3 — Failures are cached.** `timeout` and `error` results are written to the cache and replayed as `cache_hit=True` on later runs. Cache only `ok`/`partial` results. Add a **"Re-run (bypass cache)"** control on the Run page, and show `cache_hit` in the run status line. **Test:** after a timeout, an identical second run executes again (`cache_hit=False`).
- **M4 — `ar_two_column` PyMuPDF fixture isn't two-column.** Reviewer evidence: `page1_pymupdf.png` shows a single stacked column, because MuPDF's HTML layout ignores `display:flex`. The Chromium variant is correct. Generate the PyMuPDF variant with **two separate `insert_htmlbox` rectangles** (right column first in the ground truth's reading order), verify the PNG, and keep the `multi_column` tag only if both columns render side by side.
- **M5 — `header_footer` fixture has no running header/footer.** The "header" and page number are inline body text at the top, and the page numbers are Western digits while the fixture is tagged `arabic_indic_digits`. Place a real **header in the top margin** and a **footer with an Arabic-Indic page number (`— ١ —`) in the bottom margin** on each page (separate rectangles), with the body between. Ground truth order: header, body, footer. Correct the tags, and verify the PNG for both producers.

## 3. Minor fixes
- **m1:** add the lab version and an adapter implementation version (e.g. a constant `ADAPTER_VERSION` per adapter module) to the cache key, so code fixes invalidate stale cache entries.
- **m2:** label each Compare column with adapter, params, run time and `cache_hit`, and don't show stale duplicate runs of the same adapter for the same page set (show the latest by default, with an option to show all). Full ComparisonSet handling stays in E1-C.
- **m3:** treat whitespace-only text as `empty` (`text.strip()`), in all four adapters.
- **m4:**
  - `IngestService.get()`: apply the same `resolve()` + `is_relative_to` check as `original_path()`/`delete()`.
  - Wrap `LabDocument` construction so unusual PDF Info values (non-string `/Producer`/`/Creator`) are coerced to `str` or `None` instead of raising a raw `ValidationError`.
- **m5:** `tests/lab/test_ui_pages.py` uses real settings and writes into the real OS temp root. Use the `settings` fixture (tmp dir) or set `LAB_TMP_DIR` for the AppTest.
- **m6 (user decision):** remove the OpenRouter file-parser entry from `adapters.toml`, the OpenRouter/cost/ZDR keys from `lab.toml` and `settings.py`, and the "API key configured" line on Home. E1 makes no network calls.
- **m7:** fixture tags must match what is rendered (e.g. `ar_single_column` is tagged `headings` but has no heading styling). Either style the first line as a heading (larger/bold) or drop the tag.
- **m8:** cap rendered image-document pages at 4,000 px on the longest side, as for PDFs.
- **m9 (added after Claude's runtime verification, CLAUDE_REVIEW Entry 8):** Windows path length.
  - Cache files are named `.cache_<64 hex>.json.<8 hex>.tmp` inside `ws_<22 chars>/runs/`. With a deep `LAB_TMP_DIR`, the full path exceeds Windows' 260-character limit, and `atomic_write_json` raises `FileNotFoundError`. Reproduced: `test_ui_pages` and the bench both crashed.
  - Fix: shorten cache filenames (e.g. the first 32 hex characters of the key, with the full key stored inside the JSON) and the temp suffix. Turn path errors into a clear message that names the configured root.
  - Test: a `tmp_dir` whose path is at least 150 characters long must work.
- **Bench timing column:** once M2 is fixed, the bench report must show extraction time (excluding imports and overlay), labelled as such. The current "Wall ms" column is dominated by library import time (Entry 8).
- **Verification note for you:** Claude's probe scripts that will be used for re-review are described in CLAUDE_REVIEW Entry 8. Your own tests for M1–M3 must cover the same behaviours: ≥ 1 MB output, import time excluded, no replay of cached failures.

## 4. Unchanged scope
No E1-B features (variants, GT, metrics, review), no network code, no `src/` changes. Keep all existing passing behaviour, including what the user verified manually: upload, four extractors, page rendering, raw comparison.

## 5. Definition of done
All of §1–§3 are done, with tests where stated. `ruff` clean, `pytest tests/lab` green offline, ≥ 85% coverage on `lab/core`, no skip/xfail placeholders. `CODEX_REPORT_E1-A.md` maps each finding ID to the change and its evidence. Then **stop** for Claude's re-review.
