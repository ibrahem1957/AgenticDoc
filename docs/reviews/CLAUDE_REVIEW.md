# CLAUDE REVIEW LOG

Independent reviews of Codex's work. Each entry states whether verification was **static** (code reading) or **runtime** (tests/commands re-run by Claude), and approves, conditionally approves, or rejects the phase. Approval requires every AC item to be verified — Codex's self-report alone is never accepted as evidence.

## Review protocol (applies to every phase)
1. Read the PR diff in full, not only the files Codex lists.
2. Re-run `ruff check`, `pytest -m "not live"` with coverage; run live tests if a key is available.
3. Check every AC item against code + test evidence; mark each verified / failed / unverifiable.
4. Check architectural alignment with TECHNICAL_DESIGN (contracts, module boundaries, no hard-coded models, no content in logs).
5. Regression check: legacy CLI flow, previously approved phases' tests.
6. Security pass: paths, uploads, secrets, injection surfaces, error leakage.
7. Look for tests that pass trivially (mocks asserting the mock, skipped tests, over-broad `except`).
8. Findings → severity (Blocker / Major / Minor / Nit) with file:line and a concrete failure scenario.
9. Blockers/Majors → focused correction task appended to `docs/handoff/CODEX_TASK.md` (section "Correction round k"); re-review after fixes.

## Finding template
| ID | Severity | File:line | Finding | Failure scenario | Required fix | Status |
|---|---|---|---|---|---|---|

---

## Entry 0 — Planning baseline (2026-11-16)
- **Scope:** Architecture audit, research, design, plan, Phase 1 task. No implementation exists yet.
- **Verification type:** static review of `main` @ `c0a4f5a`.
- **Result:** Baseline defects D1–D20 recorded in `docs/architecture/REPOSITORY_AUDIT.md`. These are the regression reference: later phases must fix D1–D6, D9–D15 at the latest by the phase noted in the implementation plan, and must not reintroduce them.
- **Next:** ~~Review Phase 1 PR `phase-1-foundation` against AC-1.~~ Superseded by Entry 1.

## Entry 1 — Strategy change to evaluation first; E1 handoff pre-review (2026-11-16)
- **Scope:** Revised plan (IMPLEMENTATION_PLAN §0), new `EXTRACTION_LAB_DESIGN.md`, AC-E1, `CODEX_TASK.md` (Phase E1, DRAFT). The Phase 1 foundation task was withdrawn before any implementation and archived.
- **Verification type:** static self-review of the planning documents, plus a feasibility probe in a scratch venv (results in LAB §7).
- **Self-review findings on the E1 handoff**, for the user's independent review:

| ID | Severity | Item | Resolution in the draft |
|---|---|---|---|
| P1 | Major | Fixtures made by PyMuPDF could favour the PyMuPDF extractor | Second producer where available; real user documents are required for conclusions; the bench report is labelled "evidence, not verdict" |
| P2 | Major | The file-parser response shape is only partly documented (no per-page split stated) | `page_mapping="document_only"`, live fact-check required (AC-E1.16), adapter ships disabled if text is unavailable |
| P3 | Major | Seeding ground truth from one adapter biases its scores | `seeded_from` + bias flag on metrics (AC-E1.9) |
| P4 | Minor | Timing in child processes could include spawn/import cost | Timing measured inside the child around the extraction call only |
| P5 | Minor | Streamlit `unsafe_allow_html` risk with untrusted document text | Escape all text; only Lab-generated markup is unescaped |
| P6 | Minor | `.pyc` cleanup would touch `src/` | Deferred to E5 |
| P8 | **Blocker (resolved in draft)** | The feasibility probe (LAB §7) showed generated Arabic PDFs don't round-trip. Extractor CER on one sentence ranged from 0.067 to 0.90, and post-processing helps some extractors but hurts others | Ground truth = visible text; two producers + font recorded; page-1 PNG renders for visual verification; four measured variants, never global; new diagnostics. MODEL_RESEARCH §2.5 and TD §13 corrected. |
| P7 | Open | PyMuPDF is AGPL. Acceptable for a local evaluation tool; the production decision stays open until E5 | Recorded in MODEL_RESEARCH §9 |

- **Status:** handoff ready for user review. Implementation must not start until the user approves the draft. On approval, change `CODEX_TASK.md` status from DRAFT to ISSUED.
- **Next:** Review the E1 PR against AC-E1, including the manual UI walkthrough (AC-E1.15).

## Entry 2 — User requirements R1–R8 checked against the E1 draft (2026-11-16)
- **Verification type:** static review of LAB, AC-E1 and CODEX_TASK against the user's 8 requirements.
- **Already satisfied:** R1 (upload + page image beside outputs), R6 (independence, AC-E1.1–2), R7 (no automatic uploads or paid calls, AC-E1.10).
- **Gaps found and closed in the draft:**

| Req | Gap | Fix |
|---|---|---|
| R2 | Raw and cleaned were stored separately, but separate display wasn't required | Separate labelled RAW/CLEANED panes, raw always visible; byte-identity test (AC-E1.17) |
| R3 | No rule guaranteed identical pages and GT versions across extractors | `ComparisonSet`, frozen GT versions, `IncomparableRunsError`, joint re-scoring (LAB §8.1, AC-E1.18) |
| R4 | Real-document layout and producer not captured | `pdf_producer`/`pdf_creator`, `page_tags`, breakdowns, real multi-column walkthrough (AC-E1.19) |
| R5 | No rule against declaring a winner from E1 | Fixed scope statement, banned-claims test, E2 candidate pages, sets reusable by E2 (LAB §11a, AC-E1.20) |
| R8 | Only a colour diff, no individual error list | `ErrorItem` alignment, categories, number check list, Errors page, `errors.csv` (LAB §8.2, AC-E1.21) |

- **Status:** CODEX_TASK remains **DRAFT** at the user's request.

## Entry 3 — E1 issued with conditions (2026-11-16)
- **User decision:** E1 approved. Codex branches from `planning/multimodal-rag`; nothing is merged into `main`. Implementation proceeds in checkpoints E1-A (foundation, upload, rendering, local extractors), E1-B (raw/cleaned, ground truth, metrics), E1-C (errors, diagnostics, comparison sets) and E1-D (reporting, exports, security, optional file parser, final validation). All 21 AC-E1 items are preserved. The file parser stays optional. Fixtures come first; real Arabic documents are used in the final manual evaluation. Library versions are verified during implementation. PyMuPDF production licensing stays unresolved until E5.
- **Changes made:** CODEX_TASK status DRAFT → ISSUED; new branch base; §9 checkpoints with AC mapping, per-checkpoint rules and reports (`CODEX_REPORT_E1-<X>.md`); AC-E1 preamble clarifications.
- **Open findings carried forward:** P1 (fixture bias, needs real documents in the final evaluation), P2 (file-parser shape, live check in E1-D or by Claude), P7 (PyMuPDF licence, E5).
- **Next:** independent review of checkpoint E1-A once Codex pushes it and `CODEX_REPORT_E1-A.md` exists. E1-B must not start before an approval entry here.

## Entry 4 — Mandatory local Arabic OCR evaluation added to E2 (2026-11-16)
- **User decision:** local OCR model downloads and tests are approved, even if they need a GPU. Qari-OCR (NAMAA) is mandatory. Local models are compared with OpenRouter vision models on identical documents and verified GT. Accuracy outranks local vs API. No OCR selection before the user's personal review. E1 scope unchanged; Codex not interrupted.
- **Research performed (no downloads):** HF API metadata and model cards for Qari 0.4.0 / v0.3 / 0.2.2.1, PaddleOCR-VL (1.6 current, official GGUF), Nuqta 4B/0.8B (official GGUF), dots.ocr, AIN, DeepSeek-OCR, olmOCR, Baseer (not public), Surya (gated); hardware check of the evaluation laptop.
- **Key findings:**
  - No NVIDIA GPU (Iris Xe, 15.7 GB RAM), so CUDA-only paths are blocked locally.
  - Qari 0.4.0 is a LoRA adapter on Qwen3-VL-4B (4.44B params; fp32 ≈ 17.8 GB > RAM). It needs a cloud-GPU reference run, or a self-built GGUF validated against that reference.
  - Qari 0.2.2.1 targets a bitsandbytes-4bit base, which needs CUDA.
  - Vendor claims conflict (Qari's own CER 0.122 vs Nuqta's card reporting QARI CER 0.64), so neither claim is used for decisions.
- **Changes:** new `E2_OCR_EVALUATION_PLAN.md`; AC-E2 draft (16 items); E2 checkpoints E2-A … E2-D in IMPLEMENTATION_PLAN; MODEL_RESEARCH §3 and §10a; LAB §12. `CODEX_TASK.md` (E1) **not modified**.
- **Open for the user before E2 starts:** (a) whether cloud-GPU runs (Kaggle/Colab/paid instance) are acceptable for blocked candidates, and which documents may be uploaded there; (b) the E2 API/cloud-GPU budget; (c) `LAB_MODELS_DIR` location (default `D:\agenticdoc-models`, about 50–70 GB expected if all locally runnable candidates, their official GGUFs and our own Qari conversions are downloaded; AIN's 33 GB of F32 files is excluded because it isn't runnable locally [ESTIMATE]).

## Entry 5 — Self-hosted open-source models only (2026-11-16)
- **User requirement:** every AI model evaluated for potential production use must be downloadable and self-hostable on a private company server, with a verified licence (permissive preferred). Proprietary API-only models are excluded. OpenRouter is only an optional test endpoint for otherwise eligible models. Production must be able to run fully inside company infrastructure. **User approval is required before any production default.** E1-A unchanged; Codex not interrupted.
- **Research (no downloads, no installs):** HF API licence and metadata snapshot of ~75 repos; reading of licence files and cards where terms differ from tags (dots.ocr agreement, gpt-oss usage policy, Gemma 4, MiniCPM-V 4.5); HF search for Qwen3.7/3.8/4 weights and PaddleOCR Arabic models; OpenRouter catalog check for eligible test endpoints.
- **Key findings:**
  1. Licence tags are unreliable as a final answer. dots.ocr is tagged MIT but ships a custom agreement (PRC law, termination clause), so it is Class B. Many top candidates (all Qari versions, Qwen3-VL, Gemma 4, ALLaM, bge) have **no licence file** in the model repo (A-tag), so licence text must be confirmed before production.
  2. Licences differ **within** families: Qwen3.8-27B is Apache-2.0, but Qwen3.8-Flash-Next (`qwen-community-1.0`) and Qwen3.8-2.4T (`qwen3.8-max`) are custom. Qwen2.5-VL-3B is research-only and 72B uses a custom licence. Gemma 3 uses the Gemma terms, while Gemma 4 is Apache-2.0.
  3. Excluded on licence grounds: Llama 3.3/4, Gemma 3 and EmbeddingGemma, Jina v3/reranker v2 (CC-BY-NC), Command R7B Arabic (CC-BY-NC), Falcon-H1 (custom). Excluded as API-only: GPT/Gemini/Claude, API-only Qwen IDs (no Qwen3.7/Qwen4 weights), `mistral-ocr`, Cohere/Voyage rerank and embeddings, `openai/text-embedding-3-small`, `openai/gpt-4o-mini`.
  4. `openai/gpt-oss-20b/120b` are Apache-2.0 open weights with a minimal usage policy: eligible, and distinct from the excluded GPT APIs.
  5. Fanar-1-9B: the base-model chain must be checked (possible Gemma base).
- **Changes:** new `SELF_HOSTED_MODEL_SELECTION.md`; TD §0 (inference gateway, provider adapters, model registry, production egress allow-list, approval gate) + non-goal fix + change log; MODEL_RESEARCH banner; E2 plan revised (proprietary removed; PP-OCRv5 Arabic and Qwen VLMs added; OpenRouter indicative-only); AC-E2 items 1, 16–19; deferred-AC note; AC-4.3 voided/revised; IMPLEMENTATION_PLAN (new E4R retrieval/chat evaluation, E5 gateway). **`CODEX_TASK.md` (E1) not modified. No production code changed.**
- **Open decisions for the user:**
  - (a) **E1-D OpenRouter file-parser adapter** (`cloudflare-ai`/`mistral-ocr`, now ineligible external services). Recommendation: **drop it from E1-D** and mark AC-E1.15h/16 "N/A by policy". Alternatively keep it as a clearly labelled non-production reference. A change to CODEX_TASK/AC-E1 needs your approval.
  - (b) The target company server specification (GPU/VRAM/RAM/OS/Docker/air-gap).
  - (c) Whether Class B models (dots.ocr, MinerU) may be evaluated.
  - (d) Whether a private/rented GPU may be used for evaluation, and which documents may go there.
  - (e) Legal contact for licence sign-off of A-tag models.

## Entry 6 — User decisions on the self-hosting strategy (2026-11-16)
1. **Approved:** OpenRouter PDF parser removed from E1-D. AC-E1.15h/16 superseded; AC-E1.10/11 revised to "no network / no credentials" (CODEX_TASK revision note + §9 E1-D; ACCEPTANCE_CRITERIA; LAB §5.2/§6).
2. No server spec yet: evaluations record measured RAM/VRAM, the actual hardware, and reproducible deployment configurations without assuming a company server (SHM §5a.2).
3. dots.ocr and MinerU are research candidates. No install or run of models with unresolved or incompatible licences without explicit approval (SHM §5a.3).
4. Local, private or rented GPUs may be considered. No rental cost or document transfer without explicit approval (SHM §5a.4).
5. Legal approval is required before production deployment (SHM §5a.5).
6. **Qari-OCR licence lead verified** (SHM §2.1a):
   - The publisher's statement (Qari-OCR Team, discussion #1) says Apache 2.0, including commercial use.
   - Revision pinned at `aa65b4a4`.
   - Base chain: `unsloth/Qwen3-VL-4B-Instruct` → `Qwen/Qwen3-VL-4B-Instruct`, both Apache-2.0 tags; the upstream GitHub LICENSE is Apache.
   - The tagged training dataset `seemorg/books-ocr` is MIT. The team didn't answer the dataset-rights questions.
   - **Security:** the repo has a pickle file `training_args.bin` that must never be loaded (AC-E2.7 updated).
   - Classification: A-tag, publisher-confirmed, priority candidate. Legal sign-off is still required for production.

## Entry 7 — E1-A independent review (2026-11-16) — **NOT APPROVED (correction round 1 issued)**
**Verification type:**
- **Static review** of Codex's *uncommitted* E1-A working tree, via a read-only snapshot copied to Claude's scratchpad (Codex's checkout wasn't modified).
- **Clean-venv install** of `lab/requirements-lab.txt` on Windows 11 / Python 3.12.10: succeeded (exit 0). Installed: streamlit 1.67.0, PyMuPDF 1.26.5, pypdfium2 5.2.0, pdfplumber 0.11.7, pypdf 6.1.1, python-bidi 0.6.6, RapidFuzz 3.14.1, pydantic 2.12.3, pillow 12.0.0.
- **Visual inspection** of the generated fixture PNG renders.
- The **user's manual UI test** (LAB §7a).
- Claude's runtime re-run of ruff/pytest/coverage and the runner probes **was interrupted at the user's request and not repeated**. Test pass/fail and coverage are therefore **unverified by Claude**.

**User's manual results** (recorded as preliminary observations, not benchmark conclusions; LAB §7a): upload, all four extractors (`ok`), page rendering and raw visual comparison work in the UI. Observed: pypdfium2 has the best preliminary readability but has diacritic/order/mixed-language issues (`Data Quality` → `Quality Data`); PyMuPDF reverses Arabic-Indic numbers (`٢٠٢٥` → `٥٢٠٢`); pypdf reverses numbers and joins words; pdfplumber's character order is severely reversed. No extractor is selected.

**Findings**

| ID | Severity | File:line | Finding | Failure scenario | Required fix | Status |
|---|---|---|---|---|---|---|
| B1 | **Blocker (process)** | branch | E1-A is uncommitted: no push, no draft PR, no `CODEX_REPORT_E1-A.md` (CODEX_TASK §9 rule 4) | Work can't be reviewed or reproduced as a unit and could be lost; AC-E1.4 has no evidence | Commit, push, draft PR → planning branch, report | Open |
| M1 | Major | `lab/core/runner.py:160-188` | `process.join()` is called before `output.get()`. Per the Python docs, a child that put data on a Queue can't exit until the data is consumed | Large multi-page outputs: join waits until `adapter_timeout_s`, then the run is reported as `timeout` and the result is lost. Not runtime-confirmed (probe interrupted); high confidence from documented behaviour | Read before join, or pass results via a file; ≥ 1 MB test | Open |
| M2 | Major | `runner.py:32-36`; `text_pypdfium2.py:64-70`; `text_pymupdf.py:22-25`; `text_pdfplumber.py:53-62` | Timing includes the library import and overlay-block construction (pypdfium2 does it per character, quadratically) | Extractor timing comparisons are biased, especially against pypdfium2 | Time only the text-extraction call; record overlay time separately | Open |
| M3 | Major | `runner.py:176-178, 234` | Timeout/error results are cached and replayed as `cache_hit` | A transient timeout keeps showing until a bypass, and the UI has no re-run control | Cache ok/partial only; UI re-run; show cache_hit | Open |
| M4 | Major | `lab/fixtures/generate_fixtures.py:86-91,101` | `ar_two_column` (PyMuPDF producer) renders as one column; MuPDF ignores flex (PNG verified) | AC-E1.6 unmet for this producer; multi-column measurements would be meaningless | Two `insert_htmlbox` rects; verify PNG | Open |
| M5 | Major | `generate_fixtures.py:52-59` | `header_footer` has no running header/footer in the margins, and is tagged `arabic_indic_digits` while its page numbers are Western (PNG verified) | AC-E1.6 unmet; header/footer noise can't be measured in E1-C | Positioned header/footer; Arabic-Indic numbers; correct tags | Open |
| m1 | Minor | `runner.py:71-89` | Cache key lacks a lab/adapter implementation version | Stale results after an adapter code fix | Add versions to the key | Open |
| m2 | Minor | `app/pages/3_Compare.py:40,55` | All runs are shown, including duplicates and different page sets, with no params/time/cache labels | Confusing comparison | Label and de-duplicate (sets in E1-C) | Open |
| m3 | Minor | all adapters (`status="ok" if text`) | Whitespace-only text counts as `ok` | Image-only pages could show `ok` for some producers | `text.strip()` | Open |
| m4 | Minor | `ingest.py:210-214, 177-190` | `get()` lacks the path-containment check; unusual PDF Info values raise a raw ValidationError | Inconsistent safety; an unfriendly error | Add the check; coerce metadata | Open |
| m5 | Minor | `tests/lab/test_ui_pages.py:25` | The test writes into the real OS temp root | Test pollution | Use tmp settings | Open |
| m6 | Minor (user decision) | `config/adapters.toml:59-76`, `lab.toml`, `settings.py:43`, `Home.py:24` | OpenRouter parser entries and key display remain | Conflicts with the self-hosted-only policy | Remove | Open |
| m7 | Minor | `generate_fixtures.py:33-37` | The `headings` tag doesn't match the rendering | Tag-based breakdowns are misleading | Style the heading or drop the tag | Open |
| m8 | Minor | `ingest.py:250-253` | Image documents are rendered without the 4,000 px cap | Very large PNGs in the viewer | Apply the cap | Open |

**Design gap found (Claude's own):** the LAB §4 contracts lacked fields required by AC-E1.9/17/18. Added as optional fields in LAB §4 and the CODEX_TASK revision note. E1-A files stay valid.

**Positive observations (static):**
- Contracts match LAB §4.
- `lab/core` has no Streamlit imports; there are no `src` imports and no network code.
- Magic-byte detection; filename sanitization that keeps Arabic; ID-only paths with containment checks; atomic JSON writes.
- Spawn-isolated adapters with timeouts; HTML-escaped text panes; localhost binding and telemetry off.
- Two producers with page-1 renders; OFL Amiri font with its licence.
- Pinned dependencies install cleanly on Windows.
- No skip/xfail placeholders.

**AC status for E1-A items:**

| Item | Status |
|---|---|
| 1 | Verified statically (no `src/` changes in `git status`) |
| 2 | Verified statically |
| 3 | Partly verified (Windows / Python 3.12 only) |
| 4 | **Unverified** (no report; re-run interrupted) |
| 6 | **Not met** (M4, M5) |
| 7 | Run/status part supported by the user's manual run; bench unverified |
| 12 | Workspace part: code and tests present (static) |
| 13 | Code and tests present (static) |
| 14 | Non-bundle part: present, but M3 |
| 15a | User-verified for a real PDF; the PNG and fixture uploads weren't reported |
| 15c | Page image user-verified; the overlay not reported |

**Verdict:** **E1-A is NOT approved.** The correction task is in `docs/handoff/CODEX_TASK_E1-A_CORRECTIONS.md`. **E1-B must not start.** The E1-B task will be prepared after the re-review approves E1-A. Re-review plan: read the committed diff, check the report's evidence, re-inspect the fixture PNGs, and run the test suite and M1/M2/M3 probes **only if the user agrees to Claude running them**.

## Entry 8 — E1-A runtime verification: baseline on Codex's uncommitted tree (2026-11-16) — **still NOT APPROVED**
**User approval:** run the full suite, coverage, fixture generation, the bench and targeted M1–M3 tests in a separate review location. Don't touch Codex's checkout. Final approval only on the **committed** corrected branch. No E1-B without explicit user approval.

**Status of Codex's corrections:** **not yet available.** `origin/phase-e1-extraction-lab` doesn't exist. Codex's checkout is still at `6020cd4` with uncommitted E1-A work, and B1 is still open. This entry is therefore a **baseline** run on a fresh read-only snapshot of that uncommitted tree (identical to Entry 7's snapshot: `diff -rq` clean). It confirms the findings at runtime. It is **not** the approval run.

**Environment:** Windows 11 Pro, Python 3.12.10, clean venv from `lab/requirements-lab.txt` (streamlit 1.67.0, PyMuPDF 1.26.5, pypdfium2 5.2.0, pdfplumber 0.11.7, pypdf 6.1.1, python-bidi 0.6.6, RapidFuzz 3.14.1, pydantic 2.12.3, pillow 12.0.0). `LAB_TMP_DIR` was a short temp root outside the repo, deleted afterwards. Logs and the harness are in Claude's scratchpad: `review_e1a/verify.sh`, `review_e1a/checks/*.py`, `review_e1a/runs/baseline_uncommitted/`.

**Commands (run from the snapshot's `Project sdaia/`):**
```
ruff check --no-cache lab tests/lab
pytest tests/lab -q -p no:cacheprovider --cov=lab.core --cov-report=term-missing
python -m lab.fixtures.generate_fixtures
python -m lab.core.bench --fixtures lab/fixtures/generated --out <run>/bench
PYTHONPATH=. python checks/review_checks.py <tmp>/probes tests/lab/data
```

**Results:**

| Check | Result |
|---|---|
| Ruff | `All checks passed!` |
| pytest | **26 passed**, 0 failed (5 SWIG deprecation warnings from PyMuPDF) |
| Coverage `lab.core` | **89% total**. `runner.py` 88% (missing 32-49, i.e. the child-process body isn't measured), `ingest.py` 90%, `bench.py` **0%**, `models.py` 100% |
| Fixture generation | exit 0; both producers (PyMuPDF and Edge/Chromium) |
| Bench | exit 0; 64 local adapter runs, all `ok`; image-only fixture → page `empty` for all 4 adapters. pdfminer prints harmless CMap warnings |
| **M1** probe: 3 pages × 600,000 Arabic chars (≈ 3.6 MB UTF-8), timeout 20 s | **FAIL, confirmed**: `status=timeout`, `pages=0`, text lost. The adapter finished, but the parent's `join()` blocked on the undrained queue |
| **M2a** probe: stub whose module import sleeps 1.5 s, instant extraction | **FAIL, confirmed**: `wall_ms=1505` (import counted as extraction) |
| **M2b** real adapters, 1-page fixture | PyMuPDF wall 114.7 ms vs per-page 6.1 ms; pdfplumber 107.9 vs 2.7; pypdfium2 16.8 vs 9.8 (per-page *includes* overlay construction); pypdf 5.0 vs 1.4. The bench's "Wall ms" column mainly measures **library import time**, so it misleadingly makes PyMuPDF and pdfplumber look ~10× slower. No separate overlay timing exists |
| **M3** probe: adapter that times out on the first call only | **FAIL, confirmed**: the second identical call returned the cached `timeout` with `cache_hit=True` and never executed. The third call also replayed the cache. No re-run control in the UI |
| Fixture renders (regenerated) | `ar_two_column` PyMuPDF: **still one column** (M4 open). `header_footer`: unchanged generator, **M5 open**. Chromium variants correct |
| `src/` | no changes (`git status` of Codex's checkout) |

**New finding:** **m9 (Minor, Windows MAX_PATH).** Long cache filenames (`.cache_<64 hex>.json.<8 hex>.tmp`) under a deep `LAB_TMP_DIR` exceed 260 characters, so `atomic_write_json` raises `FileNotFoundError` and both `test_ui_pages` and the bench crash. Reproduced on Claude's first harness run with the scratchpad as the temp root. Added to the correction task, together with the bench timing-column requirement.

**Harness issues (Claude's own, fixed before the reported run):** the probe script lacked `PYTHONPATH=.`, and the deep scratchpad temp root triggered m9. The numbers above come from the fixed run.

**Open:** B1, M1, M2, M3, M4, M5 (and minors m1–m9).
**Verdict:** **E1-A NOT APPROVED.** Waiting for Codex's committed corrections and `CODEX_REPORT_E1-A.md`. Re-review: `verify.sh <review worktree of origin/phase-e1-extraction-lab> corrected_r1`, PNG inspection, diff and report reading. **E1-B not started; it requires explicit user approval after E1-A is approved.**
