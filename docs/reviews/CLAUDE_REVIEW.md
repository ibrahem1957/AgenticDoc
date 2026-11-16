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
