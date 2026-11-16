# AgenticDoc — Model Research, Arabic OCR Evaluation & Technology Selection

> **SUPERSEDED IN PART (2026-11-16): self-hosting requirement.** Every model considered for production must be downloadable, self-hostable and eligibly licensed. The OpenRouter-first recommendations in §1 and §4–§9 (Gemini, GPT, Claude, `mistral-ocr`, `openai/text-embedding-3-small`, Cohere/Voyage rerankers, API-only Qwen IDs) are **void**. The authoritative candidate list, licence screening and exclusions are in **[SELF_HOSTED_MODEL_SELECTION.md](SELF_HOSTED_MODEL_SELECTION.md)**. Still valid here: the Arabic OCR evidence (§2), NAMAA findings (§3), the E1 probe correction (§2.5), and the evaluation method. The catalog prices below now matter only for optional OpenRouter test runs of eligible models.

**Author:** Claude · **Date:** 2026-11-16
**Catalog snapshot:** OpenRouter `GET /api/v1/models` (469 models), `/api/v1/embeddings/models`, `?output_modalities=rerank`, fetched 2026-11-16. Prices below are copied from that snapshot and **will drift**; the code must read model IDs from configuration, never hard-code them.

## 0. Evidence rules used in this document

| Label | Meaning |
|---|---|
| **[CATALOG]** | Verified in the live OpenRouter catalog on 2026-11-16 (ID, context, price, input modalities). |
| **[PUBLISHED]** | Number reported by a paper, model card or benchmark maintainer. Not reproduced by us. |
| **[VENDOR]** | Claim made by the model's own authors about their own model. Weakest evidence. |
| **[NOT TESTED]** | No measurement against AgenticDoc documents exists yet. |

**Evaluation-first update (2026-11-16):** the bake-off in §8 is now carried out interactively in the Extraction Lab ([EXTRACTION_LAB_DESIGN.md](EXTRACTION_LAB_DESIGN.md)), in this order: E1 native text-layer extractors; E2 Arabic OCR (§2, §4 shortlist, `mistral-ocr`, NAMAA Qari-OCR as an optional local adapter); E3 tables; E4 charts. Embedding, reranker and generation bake-offs (§5, §6, §8) run after E5. The candidates in §4–§6 are inputs to the Lab, not winners.

**No test has been executed against AgenticDoc documents.** No API key was available. Every recommendation below is a *provisional default* that must be confirmed or replaced by the bake-off in §8, which Codex implements in Phase 1 and runs before Phase 3/4 defaults are locked. Older independent benchmarks (2025) evaluated earlier model generations; they indicate *model families*, not the exact 2026 versions.

---

## 1. Existing models (from code)

| Component | Model | Assessment |
|---|---|---|
| Generation | `openai/gpt-4o-mini` | Still available [CATALOG] ($0.15/$0.60 per M). Mid-2024 model. Text+image+file input, so it *could* serve vision, but in KITAB-Bench (2025) the GPT-4o family had markedly worse Arabic OCR CER (0.31) than Gemini-2.0-Flash (0.13) [PUBLISHED]. Keep as the **baseline** in the bake-off; do not replace without measurement. |
| Embeddings | `openai/text-embedding-3-small` | Available [CATALOG] ($0.02/M, 8k ctx). No published Arabic-specific retrieval numbers found. Newer open multilingual models are available on OpenRouter at ≤ half the price (see §5). Arabic quality **[NOT TESTED]**. |
| OCR / document / vision / rerank | none | — |

---

## 2. Arabic OCR — independent evidence

### 2.1 KITAB-Bench (MBZUAI, ACL Findings 2025) — the main independent Arabic OCR benchmark
Source: [arXiv 2502.14949](https://arxiv.org/pdf/2502.14949), [GitHub mbzuai-oryx/KITAB-Bench](https://github.com/mbzuai-oryx/KITAB-Bench), [project page](https://mbzuai-oryx.github.io/KITAB-Bench/).

| System (2025 generation) | OCR CER ↓ | Type |
|---|---|---|
| Gemini-2.0-Flash | **0.13** (WER 0.32) | VLM (API) |
| GPT-4o | 0.31 | VLM (API) |
| Qwen-2.5-VL | 0.492 | VLM (open) |
| Tesseract | 0.54 | Traditional OCR |
| EasyOCR | 0.58 | Traditional OCR |
| PaddleOCR (classic, not -VL) | 0.79 | Traditional OCR |
| Surya | 4.95 | Traditional OCR |

[PUBLISHED] Key conclusions from the paper: VLMs beat traditional OCR by roughly 60% CER; **the best system reached only ~65% on PDF→Markdown**, and **table structure** was a named weak spot. Implication for us: Arabic table and layout extraction is *not solved* even by the best VLMs; we must validate tables explicitly and never trust a single extraction blindly.

### 2.2 Newer specialized Arabic OCR models (vendor-reported)

| Model | Base | Reported result | Evidence | Availability |
|---|---|---|---|---|
| **NAMAA Qari-OCR 0.4.0** (`NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct`) | Qwen3-VL-4B | CER 0.122 / WER 0.256 vs Qwen3-VL-4B 0.492, Qwen3-VL-8B 0.688 | [VENDOR], test set not named; trained on Islamic books/manuscripts | HF weights, Apache-2.0, **no hosted API**, GPU needed |
| **NAMAA Qari-OCR v0.3** (`NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct`) | Qwen2-VL-2B | CER 0.300 / WER 0.485; preserves layout via HTML/Markdown; diacritics; 12 fonts | [VENDOR] | HF weights, Apache-2.0, ~217k downloads, no hosted API |
| Qari-OCR paper | — | Reports Mistral OCR CER 0.210 / WER 0.440, Tesseract CER 0.436 on its own test set | [PUBLISHED] [arXiv 2506.02295](https://arxiv.org/pdf/2506.02295) | — |
| Nuqta-Arabic-OCR-4B | — | KITAB-Bench CER 0.106 (vs Gemini-2.0-Flash 0.13) | [VENDOR] [HF card](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B), single-author, recent | HF weights, local only |
| Baseer (Misraj) | fine-tuned MLLM | WER 0.25 on Misraj-DocOCR, document→Markdown | [VENDOR/PUBLISHED] [arXiv 2509.18174](https://arxiv.org/abs/2509.18174) | Not verified as callable |
| **PaddleOCR-VL** (Baidu) | 0.9B VLM | 109 languages incl. Arabic script; Arabic edit distance 0.122 (paper); OmniDocBench v1.5 SOTA overall, tables TEDS 0.9195; chart recognition across 11 chart types (off by default) | [PUBLISHED] by authors [arXiv 2510.14528](https://arxiv.org/html/2510.14528v3), [docs](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL.html) | Local deployment (PaddlePaddle), Apache-2.0, **not on OpenRouter** |

Caveat: the "0.12 CER" figures above come from different test sets and cannot be compared with each other.

### 2.3 OpenRouter's built-in PDF parsing
Source: [OpenRouter PDF docs](https://openrouter.ai/docs/features/multimodal/pdfs). [CATALOG/docs]

| Engine | What | Price |
|---|---|---|
| `mistral-ocr` | Mistral OCR for scanned PDFs / images | $2 per 1,000 pages |
| `cloudflare-ai` | PDF→Markdown (replaces deprecated `pdf-text`) | Free |
| `native` | Pass the file to a model that accepts files | Input tokens |

Limitations: max 8 images forwarded per PDF with `mistral-ocr`; returns Markdown for the whole file, **not** per-element bounding boxes, so page-level traceability must be reconstructed. Mistral's original OCR (2503) page states that it is no longer maintained and replaced by newer OCR models; which version OpenRouter routes to must be verified at run time. Useful as **one bake-off candidate and a fallback OCR engine**, not as the core extractor.

### 2.4 Dedicated OCR models on OpenRouter
Searched the catalog for `ocr`, `paddle`, `olmocr`, `qari`, `dots`: **zero hits** [CATALOG]. All OCR via OpenRouter must therefore be done either by a general VLM or by the `mistral-ocr` parser engine.

### 2.5 Arabic OCR comparison and conclusion

| Approach | Arabic printed | RTL order | Diacritics | Tables | Charts | Bounding boxes | Deploy | Cost |
|---|---|---|---|---|---|---|---|---|
| Native PDF text (PyMuPDF and others) | Exact only when the producer encoded the text layer correctly; probe shows frequent presentation forms, ligatures and digit substitution | Varies by extractor and producer; visual-order reversal observed (LAB §7) | Exact if encoded | `find_tables()` for ruled tables | No (vector only) | **Yes** | Local, CPU | Free |
| Tesseract / EasyOCR / PaddleOCR classic | Poor (CER 0.54–0.79 [PUBLISHED]) | Weak | Weak | No | No | Yes | Local | Free |
| General VLM via OpenRouter (Gemini/Qwen/GPT/Claude) | Best independent evidence (Gemini family) | Good | Variable | Moderate; known weak spot | Yes (description; numbers risky) | No / approximate | API | ~$0.5–3 per 1k pages (estimate, §7) |
| `mistral-ocr` via OpenRouter | CER 0.21 on Qari's test set [PUBLISHED] | Good | ? | Markdown tables | No | No | API | $2 / 1k pages |
| Qari-OCR 0.4 / PaddleOCR-VL (local) | Strong vendor claims | Good | Qari: yes | PaddleOCR-VL: strong | PaddleOCR-VL: yes | PaddleOCR-VL: yes | **GPU required** | Hardware |

**Recommendation: hybrid pipeline.**
1. **Native text first, but only where it is measured to be correct.** For pages with a valid text layer, extract text, spans, fonts and bounding boxes deterministically. It is free and keeps bounding boxes. **Correction (2026-11-16 probe, EXTRACTION_LAB_DESIGN §7):** Arabic text layers are *not* reliably exact. On one test sentence, extractor CER ranged from 0.067 to 0.90 depending on the PDF producer, font and extractor (presentation forms, ligatures, digit-form substitution, visual-order reversal). Whether a page's native text is trustworthy must be decided by the quality gate, using evidence from Lab phase E1, and pages that fail go to OCR.
2. **Quality gate per page.** Classify each page as `native` / `scanned` / `mixed` / `garbled` (presentation-form glyphs, `(cid:…)` artifacts, reversed tokens, near-zero text with full-page images).
3. **VLM OCR only for scanned/garbled pages** (and image regions containing text), via OpenRouter with a structured-output prompt, at 200–300 DPI.
4. **Pluggable OCR engine interface** so that `mistral-ocr` (API) and, later, a local Qari-OCR / PaddleOCR-VL adapter can be swapped in when evaluation or GPU availability justifies it.
5. OCR never substitutes for structure: headings/tables/figures are typed elements; OCR text is one field of an element.

---

## 3. NAMAA Community research

Sources: [namaa.space](https://www.namaa.space/) (JavaScript shell; the HTML contains only the title "NAMAA Community – Advancing Modern Arabic NLP & AI"), Hugging Face organization [NAMAA-Space](https://huggingface.co/NAMAA-Space) (102 models, 9 datasets; enumerated through the HF API on 2026-11-16). The GitHub org API was rate-limited during research; no GitHub-hosted tools were verified.

| Asset | 1. What it does | 2. Arabic | 3. Modalities | 4. Public | 5. Maintained | 6. API | 7. Local | 8. Useful for AgenticDoc? | 9. Evidence |
|---|---|---|---|---|---|---|---|---|---|
| **Qari-OCR-0.4.0-VL-4B** | Arabic OCR LoRA adapter on Qwen3-VL-4B-Instruct (4.44B params) | Arabic-only; optimized for printed Islamic texts; "may vary on modern fonts" | Image → text | Yes, Apache-2.0 | Updated 2026-02-01 | **None** (card: "isn't deployed by any Inference Provider") | Yes; GPU recommended (bf16 ≈ 8.9 GB) | **MANDATORY E2 candidate (user decision 2026-11-16)**, together with v0.3 and 0.2.2.1. See E2_OCR_EVALUATION_PLAN. Domain mismatch risk for modern business/academic docs. | [VENDOR] CER 0.1222 / WER 0.2562, test set unnamed; contradicted by a third-party claim (QARI CER 0.64 on Misraj-DocOCR, Nuqta card) |
| **Qari-OCR-v0.3-VL-2B** | Arabic OCR with HTML/Markdown structure | Diacritics, 12 fonts, low-res | Image → structured text | Yes, Apache-2.0 | 2025-06 | None | Yes, GPU (smaller) | Candidate local adapter; v0.2 better on raw text per its own card | [VENDOR] CER 0.300 / WER 0.485 |
| Qari-OCR-0.2.2.1 / 0.1 | Earlier Qari versions | Arabic | Image → text | Yes | 2025 | None | Yes | Superseded | [VENDOR] |
| **GATE-Reranker-V1** | Arabic cross-encoder reranker (AraBERT base, 0.1B) | Arabic only | Text | Yes, Apache-2.0 | 2025-04 | None | Yes, CPU-feasible | **Not default.** 512-token limit, Arabic-only (we need AR↔EN), numbers only in unreadable plot images, comparison models unnamed. Possible eval candidate. | [VENDOR] |
| Namaa-ARA-Reranker-V1, Namaa-Reranker-v1 | Arabic rerankers | Arabic | Text | Yes | 2025-04 | None | Yes | Same limits as above | Low downloads, no readable metrics |
| AraModernBert-Base-STS | Arabic sentence similarity | Arabic | Text | Yes | 2025-03 | None | Yes | Not suitable as main embedder (Arabic-only; no cross-lingual) | [VENDOR] |
| **Ara-Prompt-Guard V0/V1** | Arabic prompt-injection / jailbreak classifier (Llama-Prompt-Guard-2-86M fine-tune) | Arabic | Text | Yes, Apache-2.0 | 2026-03 | None | Yes, CPU | **Optional, later.** Card states "specific quantitative metrics are not yet available". Not a substitute for structural injection defenses. | [VENDOR], no metrics |
| `QariOCR-v0.3-markdown-mixed-dataset` (37k), `Qari-0.1-eval` (50 rows, 800×800, news + Moroccan dialect) | OCR training / eval data | Arabic | Image+text | Yes; **Qari-0.1-eval has no license tag** | 2025 | — | — | Qari-0.1-eval: local smoke-test only, do not redistribute | HF dataset page |
| `Ar-Reranking-Eval`, `Arabic-Reranking-Triplet-5-Eval`, `Ara-TyDi-Triplet`, `mteb-eval-mrtydi` | Arabic retrieval / reranking eval & training data | Arabic | Text | Yes | 2024 | — | — | **Useful** for the Arabic retrieval evaluation set (check licenses) | HF |
| halluscoring-*, aragenre-*, araseg-*, BAREC-*, dialect, ASR | Classification / NER / ASR research artifacts | Arabic | Text / audio | Yes | 2026 | — | — | Not relevant to document RAG | HF |

**NAMAA gaps (explicit):** no publicly available NAMAA solution was found for **Arabic document layout analysis, Arabic PDF parsing, Arabic table structure extraction, chart understanding, or a cross-lingual (AR↔EN) embedding model**. No NAMAA model is callable through OpenRouter or any hosted inference provider.

---

## 4. Vision-language candidates (OpenRouter) [CATALOG]

Shortlist chosen for cost-feasibility at page scale (input $/M, output $/M, context). All accept image input.

| Model ID | In | Out | Ctx | Why shortlisted |
|---|---|---|---|---|
| `google/gemini-3.1-flash-lite` | 0.25 | 1.50 | 1M | Gemini family led KITAB-Bench 2025; low cost |
| `google/gemini-3.5-flash-lite` | 0.30 | 2.50 | 1M | Newer flash-lite generation |
| `google/gemini-3.7-flash` | 0.75 | 3.75 | 1M | Higher-quality tier for Stage-2 chart/table analysis |
| `qwen/qwen3-vl-235b-a22b-instruct` | 0.21 | 1.90 | 262k | Strong open VLM; Qwen family is the base of Qari/Baseer-style Arabic OCR fine-tunes |
| `qwen/qwen3.7-flash` | 0.03 | 0.13 | 1M | Very cheap; quality unknown for Arabic OCR |
| `openai/gpt-5.6-luna` | 0.20 | 1.20 | 1.05M | Low-cost OpenAI tier |
| `anthropic/claude-haiku-5.5` | 0.10 | 0.50 | 1M | Low-cost Anthropic tier |
| `openai/gpt-4o-mini` | 0.15 | 0.60 | 128k | Current model; baseline |
| `mistral-ocr` engine (file-parser) | $2 / 1k pages | | | Dedicated OCR baseline |

No 2026 independent Arabic OCR results were found for any of these exact versions. Selection must come from the bake-off.

## 5. Embedding candidates [CATALOG]

| Model ID | $/M | Ctx | Notes |
|---|---|---|---|
| `openai/text-embedding-3-small` (current) | 0.02 | 8k | Baseline |
| **`qwen/qwen3-embedding-8b`** | 0.01 | 40k | 100+ languages; #1 on MTEB multilingual (score 70.58) as of 2025-06-05 [VENDOR, [HF card](https://huggingface.co/Qwen/Qwen3-Embedding-8B)]; instruction-aware (query instruction recommended in English); MRL 32–4096 dims; Apache-2.0 → local fallback possible |
| `baai/bge-m3` | 0.01 | 8k | Widely used multilingual dense model; open weights → local fallback |
| `google/gemini-embedding-2` | 0.20 | 8k | Multimodal (text+image); 10–20× price |
| `cohere/embed-5-fast` / `-pro` | 0.08 / 0.12 | 128k | Multilingual, text+image |
| `intfloat/multilingual-e5-large` | 0.01 | **512** | Context too short for structured chunks |
| `nvidia/nemotron-3.5-embed-8b:free` | 0 | 32k | Free tier; rate limits and retention policy of free endpoints must be checked |

Arabic-specific embedding evidence: ArabicMTEB / Swan ([arXiv 2411.01192](https://arxiv.org/pdf/2411.01192)) evaluates Arabic incl. cross-lingual retrieval, but its published tables do not include the models above. **Arabic and cross-lingual retrieval quality is [NOT TESTED] for every candidate.**

## 6. Reranker candidates

OpenRouter exposes `POST /api/v1/rerank` with `{model, query, documents, top_n}` ([docs](https://openrouter.ai/docs/api/api-reference/rerank/create-rerank)). Catalog rerank models [CATALOG]: `cohere/rerank-5-fast`, `cohere/rerank-5-pro`, `cohere/rerank-4-*`, `cohere/rerank-v3.5`, `qwen/qwen3-reranker-0.6b`, `qwen/qwen3-reranker-8b`, `mongodb/rerank-3`, `mongodb/rerank-3-lite`, `nvidia/nemotron-3.5-rerank-8b:free` (text+image). The catalog shows $0 per token for rerankers, so pricing is probably per search request — **verify in the per-model page before enabling.**

**Recommendation:** reranking **off by default**; implement behind a flag and enable only if the retrieval evaluation shows ≥ +5 points Recall@5 or MRR@10 on the Arabic and cross-lingual sets (Phase 4 gate). First candidate: `qwen/qwen3-reranker-8b` (same family as the embedder, multilingual); second: `cohere/rerank-5-fast`.

## 7. Cost model (estimates — to be replaced by measured values)

Assumptions: dense Arabic page image ≈ 1.0–1.6k input tokens (provider-dependent image tokenization) and ≈ 0.8–1.2k output tokens.

| Operation | Model (provisional) | Est. cost |
|---|---|---|
| OCR of 1,000 scanned pages | `google/gemini-3.1-flash-lite` | ≈ $1.5–2.2 |
| OCR of 1,000 scanned pages | `mistral-ocr` engine | $2.00 (published) |
| Embedding a 100-page native PDF (~60k tokens) | `qwen/qwen3-embedding-8b` | ≈ $0.0006 |
| One chat answer (6k context in, 500 out) | `openai/gpt-4o-mini` | ≈ $0.0012 |
| Native-text pages | none | $0 |

The cost logger (Phase 1) must record actual `usage` from every response so these estimates can be replaced.

## 8. Mandatory bake-off (executed by Codex, reviewed by Claude)

Implemented in Phase 1 (harness) and executed at the start of Phase 3 (OCR/vision) and Phase 4 (embeddings/rerank). Results go to `docs/architecture/MODEL_EVAL_RESULTS.md` with raw outputs committed under `eval/results/`.

| Bake-off | Data | Metrics | Candidates |
|---|---|---|---|
| Arabic OCR | Synthetic Arabic/mixed pages with exact ground truth (fonts, diacritics, Arabic-Indic & Western digits, 2-column, headers/footers) rendered at 300/150/100 DPI + noise; KITAB-Bench subset (license permitting); `Qari-0.1-eval` (local only) | CER, WER, numeric exact match, reading-order (Kendall τ over blocks), latency, $/page | §4 shortlist + `mistral-ocr` |
| Arabic tables | Synthetic tables with known cells (native + scanned) | Cell exact match, numeric exact match, TEDS | Native `find_tables`, best 2 VLMs |
| Charts | matplotlib charts with known values (labeled / unlabeled), Arabic labels | Labeled-value exact match, unlabeled abstention rate, hallucinated-value rate | Best 2 VLMs |
| Embeddings | AR→AR, AR→EN, EN→AR, mixed queries over the synthetic + real corpus (≥ 150 queries) | Recall@1/5/10, MRR@10, latency, cost | §5 top 4 |
| Reranker | Same | ΔRecall@5, ΔMRR@10 | §6 top 2 |
| Generation | 60 grounded QA items (AR/EN, single/multi-doc, unanswerable) | Answer correctness (LLM-judge + manual spot check), citation validity, refusal accuracy, language match, cost | `openai/gpt-4o-mini`, `anthropic/claude-haiku-5.5`, `openai/gpt-5.6-luna`, `google/gemini-3.5-flash-lite` |

Decision rule (from the project brief): correctness and grounding first, then Arabic accuracy, structure, retrieval, cost, latency, maintainability. A cheaper model is chosen only if it is within the tolerance stated in `ACCEPTANCE_CRITERIA.md`.

---

## 9. Model selection table (provisional, pending §8)

| Component | Existing | Candidates | Arabic quality evidence | Cost | Provisional recommendation |
|---|---|---|---|---|---|
| Generation LLM | `openai/gpt-4o-mini` | `claude-haiku-5.5`, `gpt-5.6-luna`, `gemini-3.5-flash-lite`, `qwen3.7-plus` | None independent for 2026 versions | $0.10–0.32 in / $0.50–2.50 out | **Keep `openai/gpt-4o-mini` as default** until the generation bake-off shows a candidate is better; make configurable. |
| Vision (Stage-1 descriptions, Stage-2 analysis) | none | §4 | Gemini family best on KITAB-Bench 2025 [PUBLISHED] | $0.25–0.75 in | **`google/gemini-3.1-flash-lite`** for Stage 1; **`google/gemini-3.7-flash`** for Stage 2 (detail/numbers). |
| Arabic OCR (scanned pages) | none | VLMs, `mistral-ocr`, local Qari/PaddleOCR-VL | §2 | ~$2 / 1k pages | **VLM OCR with `google/gemini-3.1-flash-lite`**, `mistral-ocr` as configured fallback engine; local adapters optional later. |
| PDF parser | none | PyMuPDF, pdfplumber/pdfminer, pypdfium2, Docling, OpenRouter file-parser | PyMuPDF performs bidi reordering (pdfium does not, per [pdftext README](https://github.com/datalab-to/pdftext)); presentation-form normalization still needed | Free | **PyMuPDF** (see licensing note) with Arabic normalization + quality gate. |
| Embeddings | `openai/text-embedding-3-small` | §5 | None independent for Arabic | $0.01–0.20 | **`qwen/qwen3-embedding-8b`**, fallback `baai/bge-m3`; keep current model as baseline. |
| Sparse retrieval | none | BM25 with Arabic normalization | — | Free | **Include behind a flag**, enabled if eval shows gain (exact numbers/codes/names usually benefit). |
| Reranker | none | §6, GATE-Reranker-V1 | None | per request | **Off by default**; evaluate `qwen/qwen3-reranker-8b`. |
| Prompt-injection classifier | none | Ara-Prompt-Guard | No metrics | — | **Not adopted**; structural defenses only. |

### Why alternatives were rejected (summary)
- **Traditional OCR (Tesseract/EasyOCR/PaddleOCR classic):** 4–6× worse Arabic CER than the best VLM in the only independent benchmark.
- **Local Qari / PaddleOCR-VL as default:** require a GPU and model serving; the user prefers OpenRouter. Retained as optional adapters.
- **Sending every page to a VLM:** violates the cost rule and is less exact than native text for digital PDFs.
- **OpenRouter file-parser as main extractor:** no per-element bounding boxes or element types; 8-image cap.
- **`multilingual-e5-large`:** 512-token context.
- **`gemini-embedding-2` / Cohere embed:** 8–20× more expensive; adopt only if the bake-off shows a clear gain.

### Licensing constraint requiring a user decision
**PyMuPDF is AGPL-3.0** (or commercial license from Artifex). AGPL obligations extend to network services. This is compatible with a public open-source repository like the current one, but **not** with a closed-source deployment. If the project may become closed-source, the alternative is `pypdfium2` (Apache-2.0/BSD) + `pdfplumber` (MIT), with extra work for Arabic bidi ordering. The extractor is behind an interface either way. **Default chosen: PyMuPDF.**

## 10. Data retention (third-party)

- OpenRouter does not store prompts/responses by default; opt-in logging exists; content flagged as potential CSAM may be retained ([OpenRouter data collection](https://openrouter.ai/docs/guides/privacy/data-collection)).
- Upstream providers have their own policies. Per-request routing controls exist: `provider.data_collection: "deny"` (only providers that do not collect data) and `provider.zdr: true` (only Zero-Data-Retention endpoints) ([provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)).
- **We do not assume zero retention.** The backend sends `data_collection: "deny"` by default, and `zdr: true` when `AGENTICDOC_REQUIRE_ZDR=true`. Some models may have no ZDR endpoint; the request then fails, and the error must be explicit.
- Local session deletion **cannot** delete data already sent to a provider. This is stated in API docs and the README.

## 10a. Local Arabic OCR update (2026-11-16)
The user approved downloading and testing local OCR models, including GPU-only ones. Qari-OCR is mandatory, and accuracy outranks local vs API. The candidate set, licences, sizes, CPU/GPU feasibility on the evaluation laptop (i7-1255U, 15.7 GB RAM, **no NVIDIA GPU**), execution paths, download safety and metrics are in **[E2_OCR_EVALUATION_PLAN.md](E2_OCR_EVALUATION_PLAN.md)**. Summary:
- **Mandatory local:** Qari-OCR 0.4.0, v0.3 and 0.2.2.1 (NAMAA); PaddleOCR-VL 1.6 (official GGUF + PaddleOCR pipeline).
- **Added:** Nuqta-Arabic-OCR 4B/0.8B, Apache-2.0, official GGUF. It has the strongest published Arabic numbers ([VENDOR] KITAB-Bench CER 0.106), and its card notes training overlap with KITAB-Bench test images. Also dots.ocr (MIT), AIN-7B (MIT, GPU-only here), DeepSeek-OCR (MIT, CUDA-only), and Tesseract as the floor baseline.
- **Not publicly available:** Baseer / Baseer v2 (HTTP 401).
- §9's "local adapters optional later" for OCR is **superseded**: local candidates are first-class in E2.

## 11. Sources
- OpenRouter models API: https://openrouter.ai/api/v1/models (snapshot 2026-11-16)
- OpenRouter PDF processing: https://openrouter.ai/docs/features/multimodal/pdfs
- OpenRouter rerank API: https://openrouter.ai/docs/api/api-reference/rerank/create-rerank
- OpenRouter provider routing: https://openrouter.ai/docs/guides/routing/provider-selection
- OpenRouter data collection: https://openrouter.ai/docs/guides/privacy/data-collection
- KITAB-Bench: https://arxiv.org/pdf/2502.14949 · https://github.com/mbzuai-oryx/KITAB-Bench
- QARI-OCR paper: https://arxiv.org/pdf/2506.02295
- NAMAA: https://www.namaa.space/ · https://huggingface.co/NAMAA-Space
- Qari-OCR 0.4.0: https://huggingface.co/NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct
- Qari-OCR v0.3: https://huggingface.co/NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct
- GATE-Reranker-V1: https://huggingface.co/NAMAA-Space/GATE-Reranker-V1
- Ara-Prompt-Guard V1: https://huggingface.co/NAMAA-Space/Ara-Prompt-Guard_V1
- Qari-0.1-eval: https://huggingface.co/datasets/NAMAA-Space/Qari-0.1-eval
- Qari-OCR 0.2.2.1: https://huggingface.co/NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct
- Nuqta-Arabic-OCR 4B / GGUF: https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B · https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B-GGUF
- PaddleOCR-VL 1.6 / GGUF: https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6 · https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF
- dots.ocr: https://huggingface.co/dots-studio/dots.ocr
- AIN: https://huggingface.co/MBZUAI/AIN
- DeepSeek-OCR: https://huggingface.co/deepseek-ai/DeepSeek-OCR
- Qwen3-VL-4B-Instruct (Qari 0.4 base): https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
- Nuqta-Arabic-OCR-4B: https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B
- Baseer: https://arxiv.org/abs/2509.18174
- PaddleOCR-VL: https://arxiv.org/html/2510.14528v3 · https://www.paddleocr.ai/latest/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL.html
- Qwen3-Embedding-8B: https://huggingface.co/Qwen/Qwen3-Embedding-8B
- Swan / ArabicMTEB: https://arxiv.org/pdf/2411.01192
- pdftext (bidi note): https://github.com/datalab-to/pdftext

## 12. Research limitations
- No runtime test was possible; no exact 2026 model versions have independent Arabic OCR results.
- The NAMAA website could not be read beyond its title (client-rendered); findings rely on the HF organization.
- Rerank pricing and the OpenRouter `usage`/cost response fields must be verified against live docs during Phase 1.
