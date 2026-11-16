# CODEX REPORT — Phase E1-A: Extraction Lab foundation + correction round 1

> **Authorship:** E1-A and most of correction round 1 were implemented by **Codex**. Codex hit its usage limit before committing. **Claude took over** (user instruction, 2026-11-16), continued from Codex's staged work without discarding it, completed the remaining corrections, verified, committed and pushed. Codex's pre-takeover state is preserved at `refs/backup/e1a-codex-wip-2026-11-16` (object `7cf8d17`, local) and in a scratchpad tar. **This report and its review are a self-review by the implementer, not an independent review.**

**Branch:** `phase-e1-extraction-lab` (pushed to origin) · **Base:** `6020cd4` (planning) · **Head (implementation):** `3095b33956b3b7ca9c4817739f15146dd41328e2` · **Date:** 2026-11-16
**Draft PR:** **not created by Claude.** `gh pr create` failed with `GraphQL: must be a collaborator (createPullRequest)`: the GitHub CLI is logged in as `ialtowalah`, which isn't a collaborator on `ibrahem1957/AgenticDoc` (git pushes use a different stored credential). The user should open it with one click: <https://github.com/ibrahem1957/AgenticDoc/compare/planning/multimodal-rag...phase-e1-extraction-lab?expand=1> (choose **Create draft pull request**; don't merge).
**Task references:** `docs/handoff/CODEX_TASK.md` (§9 E1-A) and `docs/handoff/CODEX_TASK_E1-A_CORRECTIONS.md` (B1, M1–M5, m1–m9).

## 1. Summary
The E1-A lab is committed and pushed:
- upload with magic-byte validation;
- temporary workspaces with TTL and safe paths;
- page rendering;
- four local text adapters in isolated child processes;
- a cache;
- a fixture generator with two producers;
- a headless bench;
- a Streamlit UI (Home, Documents, Run, Compare raw).

All correction-round findings are addressed. Claude found and fixed two further defects during takeover: timing that started after page/text-page loading (Codex's M2 fix moved the bias rather than removing it), and **Streamlit binding to all network interfaces plus an external IP lookup** when launched as documented. Production `src/` is unchanged. E1-B wasn't started.

## 2. Files
59 files, 3,859 insertions (commit `3095b33`). By area:

| Area | Paths |
|---|---|
| Core | `lab/core/{models,workspace,ingest,runner,settings,bench}.py`, `lab/core/adapters/{base,registry,text_pymupdf,text_pypdfium2,text_pdfplumber,text_pypdf}.py` |
| UI | `lab/app/Home.py`, `lab/app/components.py`, `lab/app/pages/1_Documents.py … 6_Results_and_Export.py` (pages 4–6 are placeholders) |
| Launcher (new, Claude) | `lab/launch.py` |
| Config | `lab/config/{lab,adapters}.toml`, `lab/.streamlit/config.toml`, `lab/requirements-lab.txt` |
| Fixtures | `lab/fixtures/generate_fixtures.py`, `lab/fixtures/fonts/Amiri-Regular.ttf` + `OFL.txt`, `lab/fixtures/README.md` |
| Tests | `tests/lab/test_{models,workspace,ingest,adapters_local,runner,fixtures,ui_pages,ui_no_pandas,no_src_changes,bench,launch}.py`, `stub_adapters.py`, `slow_import_adapter.py`, `data/` (synthetic `text.pdf`, `image_only.pdf`, `image.png`) |
| Docs | `lab/README.md`, root `README.md` (Extraction Lab section), `docs/architecture/E1_FIXTURE_BENCH.md`, `.gitignore` |

Not committed (git-ignored or outside the repo): `lab/fixtures/generated/`, `__pycache__/`, workspaces under `%TEMP%`, bench output, coverage data.

## 3. Findings: root cause → fix → evidence

| ID | Root cause | Fix (who) | Regression evidence |
|---|---|---|---|
| **B1** | Work was uncommitted, with no push, PR or report | Committed `3095b33` and pushed (Claude); this report. **The PR couldn't be created (permissions), see header** | `git ls-remote` = `3095b33` |
| **M1** | Parent `join()`ed before draining a `multiprocessing.Queue`; a child with > pipe-buffer output can't exit until it's read | Child sends over a `Pipe`; parent polls and `recv()`s before `join` against one deadline (Codex) | `test_large_child_payload_is_received_without_deadlock` (3 × 600k chars); Claude's probe M1: `ok`, text intact, ~3.6 MB |
| **M2** | Timer started before module import. Codex's fix then started per-page timers after page load / `get_textpage()` and summed per-page times only, which excluded document open and pdfium's character parsing, so pypdfium2 was understated | Import and adapter construction → `startup_ms` (Codex). Extraction = `adapter.run()` duration minus `overlay_ms`; per-page timers start before page/text-page loading; `ADAPTER_VERSION` bumped to 3 to invalidate cached timings (Claude) | `test_import_time_is_separate_from_extraction_time`, `test_document_open_counts_as_extraction_time` (new), `test_overlay_time_is_excluded_from_extraction_time` (new); Claude's probe M2a (1.5 s import → extraction 0 ms) |
| **M3** | Every result, including timeout/error, was cached and replayed | Only `ok`/`partial` are cached or read; UI **Re-run (bypass cache)**; `cache_hit` shown (Codex) | `test_timeout_is_not_cached_and_second_run_executes`; Claude's probe M3: timeout → rerun executes → `ok`; success still cached |
| **M4** | MuPDF's HTML engine ignores `display:flex`, so the "two-column" fixture rendered as one column | Two `insert_htmlbox` rectangles, right column first (Codex) | `test_pymupdf_two_column_fixture_uses_side_by_side_rectangles`; **visual check (Claude): two columns, right first, both producers** |
| **M5** | "Header/footer" was inline body text; page numbers were Western digits while tagged Arabic-Indic | Separate header/body/footer rectangles in the margins; Chromium absolute-positioned header/footer; `— ١ —` (Codex) | `test_header_footer_fixture_uses_margins_and_arabic_indic_page_number`; **visual check: header top, footer bottom with `— ١ —`, both producers** |
| m1 | Cache key lacked implementation versions | Key adds lab version + `ADAPTER_VERSION` (Codex) | `test_cache_key_includes_lab_and_adapter_implementation_versions` |
| m2 | Compare showed every run without labels | Page-set selector, latest run per adapter by default, "show all" option, params/timing/`cache_hit` caption (Codex) | `test_compare_uses_latest_duplicate_run_by_default`; AppTest asserts the caption |
| m3 | Whitespace-only text counted as `ok` | `text_status()` uses `strip()` (Codex) | `test_whitespace_only_text_is_empty` |
| m4 | `get()` had no containment check; odd PDF Info values raised a raw ValidationError | `resolve()` + `is_relative_to`; `_metadata_text()` coercion (Codex) | `test_get_rejects_document_path_traversal`, `test_unusual_pdf_metadata_is_coerced_without_validation_error` |
| m5 | UI test wrote into the real temp root | Uses the `settings` fixture + `LAB_TMP_DIR` (Codex) | `test_documents_run_and_compare_without_dataframe_import_path` |
| m6 | OpenRouter remnants (config, settings, Home line) | Removed; `requests`/`python-dotenv` dropped from requirements (Codex) | `test_e1_configuration_has_no_openrouter_or_network_settings`; grep of `lab/` and `tests/` finds no network code |
| m7 | `headings` tag without heading styling | `<h1>` heading for tagged fixtures (Codex) | `test_heading_tag_matches_larger_heading_render`; visual check |
| m8 | Image documents rendered without the 4,000 px cap | `thumbnail((4000, 4000))` (Codex) | `test_large_image_render_is_capped_at_4000_pixels` |
| m9 | `.cache_<64 hex>.json.<8 hex>.tmp` under a deep root exceeded Windows MAX_PATH | `c_<24 hex>.json` with the full key stored inside; short temp names; clear `WorkspaceError` naming the root (Codex) | `test_deep_windows_cache_path_remains_short` (≥ 170-char root), `test_invalid_configured_root_has_clear_error` |
| **N1 (new, Claude)** | Streamlit loads `.streamlit/config.toml` only from the CWD. Launched from `Project sdaia` as the README said, it **bound `0.0.0.0`/`::`**, printed Network/External URLs (an **external IP lookup**), and enabled browser usage stats | `python -m lab.launch` always passes `--server.address 127.0.0.1 --browser.gatherUsageStats false --server.maxUploadSize 50`, rejects overrides of the first two, and puts options before the script path. README updated | `tests/lab/test_launch.py` (argv order, protected options, README instruction); runtime: listener `127.0.0.1:8599` only, LAN address refused, startup log shows only the local URL, **0 non-loopback connections** |
| N2 (Claude) | `bench.py` had 0% coverage | `tests/lab/test_bench.py` (adapters, labelled timing columns, scope wording, workspace cleanup) | coverage of `bench.py` 85% |

## 4. Commands run and results (Claude, 2026-11-16)
Environment: Windows 11 Pro, Python 3.12.10, a **fresh venv** from `lab/requirements-lab.txt` (installed: streamlit 1.67.0, PyMuPDF 1.26.5, pypdfium2 5.2.0, pdfplumber 0.11.7, pypdf 6.1.1, python-bidi 0.6.6, RapidFuzz 3.14.1, pydantic 2.12.3, pillow 12.0.0, pytest 8.4.2, pytest-cov 7.0.0, ruff 0.14.3; install exit 0). `LAB_TMP_DIR` = a short temp root outside the repo.

```text
ruff check --no-cache lab tests/lab                → All checks passed!
pytest tests/lab -q --cov=lab.core                 → 52 passed, 0 failed, 0 skipped (19.3 s)
  coverage lab.core TOTAL 93%  (runner 82%: the child-process body runs in a subprocess and isn't measured; bench 85%; ingest 91%; workspace 92%; models/settings/pymupdf/pdfplumber/pypdf 100%)
python -m lab.fixtures.generate_fixtures           → exit 0 (PyMuPDF + Edge/Chromium producers)
python -m lab.core.bench --fixtures lab/fixtures/generated --out <tmp>
                                                   → 64 local adapter runs, all ok; image-only → page "empty" for all 4
reviewer probes (review_checks.py)                 → M1 PASS, M2a PASS, M3 PASS (failures=0)
git diff origin/planning/multimodal-rag --stat -- "Project sdaia/src"   → empty
python -m lab.launch --server.headless true --server.port 8599
                                                   → listens 127.0.0.1:8599 only; LAN 172.24.64.1:8599 refused;
                                                     log "URL: http://127.0.0.1:8599" only; no non-loopback TCP connections
```
Codex's earlier figures (44 passed, 88%) are superseded by the run above (52 tests after Claude's additions).

## 5. Benchmark
`docs/architecture/E1_FIXTURE_BENCH.md`: 64 runs (8 fixtures × 2 producers where applicable × 4 adapters, plus the image-only fixture). Synthetic evidence only, **not an extractor verdict**. Extraction CPU ms has ~15.6 ms resolution on Windows, so small values show 0.00.

## 6. UI verification
- **Automated:** Streamlit `AppTest` drives Documents, Run (four extractors preselected, re-run checkbox) and Compare (RAW pane, labelled caption) on a real PDF and real adapter runs.
- **Runtime:** server started via the launcher; health OK; localhost-only; no external connections.
- **Not verified on the corrected build:** an interactive browser walkthrough (upload → preview → run four extractors → RAW comparison with Arabic display → re-run). No browser automation was available. The **user's earlier manual walkthrough** (pre-correction build: upload, four extractors `ok`, rendering, RAW comparison) remains the latest interactive evidence. **The user needs to repeat it with `python -m lab.launch`.**

## 7. Design deviations
1. New `lab/launch.py` entry point (N1). `streamlit run lab/app/Home.py` is no longer the documented launch method.
2. `RunResult.startup_ms` / `overlay_ms` and `PageResult.overlay_ms` / `extraction_cpu_ms`, plus `AdapterInfo.implementation_version`: additive optional fields, not in the original LAB §4.
3. `RunResult.wall_ms` means **extraction time** (`run()` minus overlay), not total child time.
4. Cache file format `{"cache_key", "result"}` under `c_<24 hex>.json`.

## 8. Known limitations / open issues
- PR not created (permissions), see header.
- Interactive UI walkthrough of the corrected build pending (user).
- Python 3.11/3.13 and Linux not verified (Windows/3.12 only).
- `runner.py` coverage excludes the subprocess body (exercised by tests and probes, but not measured).
- Timing is single-run and laptop-based; CPU ms has coarse resolution.
- AC-E1.15b/d/e/f/g, 17–21 belong to E1-B…E1-D and aren't claimed here.
- PyMuPDF licensing (AGPL) remains unresolved for production by design (E5).

## 9. Questions for Claude (reviewer) / the user
- Approve E1-A after the interactive walkthrough with `python -m lab.launch`?
- Open the draft PR via the link above (or grant `ialtowalah` collaborator access).
