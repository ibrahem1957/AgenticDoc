# E2 — Arabic OCR Evaluation Plan: Self-Hosted Open Models

**Author:** Claude · **Date:** 2026-11-16 (revised 2026-11-16 for the self-hosting requirement) · **Status:** PLANNED. Implementation starts only after E1 is complete (E1-D approved and the final E1 walkthrough done). E1's scope is unchanged by this document.
**Self-hosting requirement (supersedes the earlier "local vs cloud" framing):** only models with downloadable weights, a usable inference implementation, and an eligible licence (Class A/A-tag; Class B only with user approval) are evaluated. **Proprietary API-only models (Gemini, GPT, Claude, Qwen API-only IDs, `mistral-ocr`) are excluded.** OpenRouter is allowed only as an optional, indicative test endpoint for eligible models. Scored results come from self-hosted inference. Policy, licence evidence and the full candidate table: [SELF_HOSTED_MODEL_SELECTION.md](SELF_HOSTED_MODEL_SELECTION.md) (SHM).
**User decisions (2026-11-16), see SHM §5a:**
- No server spec is assumed. Every run records measured RAM/VRAM, the actual hardware, and a reproducible deployment configuration.
- dots.ocr and MinerU are research candidates only, with no install or run without approval.
- Local, private or rented GPUs may be used for evaluation, but no rental cost or document transfer happens without explicit approval each time.
- Legal approval is required before production.
- **Qari-OCR remains the priority Arabic candidate**, publisher-confirmed Apache 2.0 (SHM §2.1a), pinned at revision `aa65b4a4`.
**User decision (2026-11-16):** downloading and testing local OCR models is approved, even if they need a GPU. **NAMAA Qari-OCR is a mandatory candidate.** Accuracy, especially Arabic OCR accuracy, takes priority over local vs API. **No OCR solution is selected until the user has personally reviewed the comparison results.**

Evidence labels as in MODEL_RESEARCH §0: [HF-API] = Hugging Face API metadata fetched 2026-11-16; [CARD] = model card statement; [VENDOR] = the authors' own benchmark claim; [ESTIMATE] = Claude's arithmetic, to be replaced by measurement; [MEASURED] = none yet.

---

## 1. Hardware of the evaluation machine (checked 2026-11-16)

| Item | Value |
|---|---|
| CPU | Intel Core i7-1255U (10 cores / 12 threads, mobile, AVX2, no AVX-512) |
| RAM | 15.7 GB |
| GPU | Intel Iris Xe (integrated, shared memory). **No NVIDIA GPU; CUDA unavailable** (`nvidia-smi` not found) |
| Disk free | C: 57 GB, D: 189 GB |
| OS | Windows 11 Pro |

**Consequence:** every CUDA-only path (vLLM, flash-attention, bitsandbytes 4-bit, `paddlepaddle-gpu`) is a **local blocker** on this machine. Under requirement 6 a blocked candidate is **not** dropped. It is evaluated through a documented alternative (§4) or listed with its blocker in the report.

## 2. Local candidates

### 2.1 Mandatory

| Candidate | What | Weights (official) | Licence | Size [HF-API] | Published Arabic evidence |
|---|---|---|---|---|---|
| **Qari-OCR 0.4.0** (`NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct`) | LoRA adapter on `Qwen/Qwen3-VL-4B-Instruct` (4.44B params, BF16) | Adapter 0.31 GB + base ≈ 8.9 GB | Apache-2.0 (adapter and base) | — | [VENDOR] CER 0.122 / WER 0.256 on an unnamed set; "optimized for printed Islamic texts; may vary on modern fonts"; 300+ DPI recommended. **Contradicting third-party claim:** Nuqta's card reports QARI at CER 0.64 / WER 0.76 on Misraj-DocOCR (version not stated) |
| **Qari-OCR v0.3** (`NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct`) | Full fine-tune of Qwen2-VL-2B; layout via HTML/Markdown | 4.42 GB (2.21B params) | Apache-2.0 | — | [VENDOR] CER 0.300 / WER 0.485 |
| **Qari-OCR 0.2.2.1** (`NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct`) | LoRA adapter on `unsloth/Qwen2-VL-2B-Instruct-unsloth-bnb-4bit` | Adapter 0.12 GB | Apache-2.0 | — | [VENDOR] v0.3 card states v0.2 has the best raw-text CER (0.061) |
| **PaddleOCR-VL 1.6** (`PaddlePaddle/PaddleOCR-VL-1.6`) | Document parsing VLM (text, tables, charts, formulas); full pipeline includes layout detection | 1.92 GB; **official GGUF** `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` | Apache-2.0 (LICENSE file present) | updated 2026-11-06 | Arabic listed among supported scripts [CARD]; Arabic edit distance 0.122 reported for the first version (paper) [VENDOR]. No 1.6-specific Arabic number |
| **PaddleOCR PP-OCRv5** (`PaddlePaddle/PP-OCRv5_server_det` + `PaddlePaddle/arabic_PP-OCRv5_mobile_rec`; ONNX variant `arabic_PP-OCRv5_mobile_rec_onnx`) | Classic detection + **Arabic-specific recognition** pipeline | < 0.1 GB | Apache-2.0 tag | 2025-10-16 | Older classic PaddleOCR measured CER 0.79 on KITAB-Bench; v5 Arabic is unmeasured. CPU-fast; contrasts with the VLM approaches |
| **Qwen3-VL (general VLM baseline)**: `Qwen/Qwen3-VL-4B-Instruct` (Qari 0.4's own base, to measure the fine-tune's gain) and `Qwen/Qwen3-VL-8B-Instruct` | General VLM OCR | 8.9 / 17.5 GB bf16 | Apache-2.0 tag | 2025-10 | Qari's card reports CER 0.49 / 0.69 on its set [VENDOR of a competing model] |

### 2.2 Additional candidates (included when feasible; they rank by published Arabic evidence)

| Candidate | What | Licence | Size | Evidence | Inclusion |
|---|---|---|---|---|---|
| **Nuqta-Arabic-OCR 4B** (`SalahALHaismawi/Nuqta-Arabic-OCR-4B`) | Arabic OCR fine-tune of Qwen3.5-4B; text/Markdown with HTML tables, reading order | Apache-2.0 | 9.75 GB; **official GGUF** Q4_K_M 2.9 GB / Q8_0 4.8 GB + mmproj 0.67 GB | [VENDOR] KITAB-Bench CER 0.106 (0.113 excluding 234 test images also present in training data); Misraj-DocOCR CER 0.121 / WER 0.246; GGUF Q4 ≈ bf16 CER; "~2.5 min per 2.4 MP page on laptop CPU, 8 threads" | **Include** (strongest published Arabic numbers; CPU-feasible) |
| Nuqta-Arabic-OCR 0.8B (+ official GGUF) | Small variant | Apache-2.0 | — | No CER published | Include as low-cost variant |
| dots.ocr (`dots-studio/dots.ocr`) | Multilingual document parser (layout JSON with bboxes, reading order, HTML tables) | **Class B**: custom "dots.ocr LICENSE AGREEMENT" on top of MIT (PRC law, termination on prohibited use; SHM §2.1) | 3B; GGUF by `ggml-org` | [VENDOR-3rd] Misraj-DocOCR CER 0.40 (from Nuqta's card); no Arabic metric from its authors | **Only with user approval** (Class B). Then: GGUF path if it runs, otherwise GPU-only, documented |
| Larger general VLMs: `Qwen/Qwen3.8-27B` (Apache-2.0, LICENSE present), `Qwen/Qwen3-VL-30B-A3B-Instruct`, `Qwen/Qwen3-VL-32B-Instruct`, `google/gemma-4-31b-it` (Apache-2.0 tag), `mistralai/Mistral-Small-3.2-24B-Instruct-2506`, `openbmb/MiniCPM-V-4_5`, `OpenGVLab/InternVL3_5-8B` | General VLM OCR; also Stage-2 visual analysis candidates (E4) | Class A / A-tag | 8.5–33B (17–67 GB bf16) | No Arabic OCR numbers | **GPU only** (P1/P2 profiles, SHM §5). Self-hosted on an approved GPU. An OpenRouter run (where available) is indicative only |
| AIN-7B (`MBZUAI/AIN`) | Arabic-English LMM (Qwen2-VL base) | MIT | 8.29B params (33 GB F32 files) | [VENDOR] KITAB-Bench CER 0.20 (via Nuqta's card); OCR & doc understanding 72.35 on its own benchmark | **GPU-only** here (bf16 ≈ 16.6 GB exceeds RAM) [ESTIMATE] → cloud-GPU path or documented blocker |
| DeepSeek-OCR (`deepseek-ai/DeepSeek-OCR`) | Multilingual OCR | MIT | 3.34B | No Arabic metric found | GPU-only per card (CUDA + flash-attn). Optional on cloud GPU |
| Tesseract 5 (`ara` traineddata) | Traditional OCR baseline | Apache-2.0 | small | KITAB-Bench CER 0.54 [PUBLISHED] | **Include as floor baseline** (CPU, cheap) |

### 2.3 Excluded, with reasons (re-check at E2 kickoff)

| Candidate | Reason |
|---|---|
| Baseer / Baseer v2 (Misraj) | Weights not publicly accessible (`Misraj/Baseer` → HTTP 401 on 2026-11-16). Reported CER 0.12 (via Nuqta's card). Include if access or an API becomes available |
| Surya | Repo gated (401); KITAB-Bench CER 4.95 [PUBLISHED] |
| olmOCR-2-7B | Trained for English-centric documents; no Arabic claim |
| Community GGUF conversions of Qari (`marwan-osama/…`, `mradermacher/…`) | Unknown conversion source, and the `marwan-osama` repo states no licence. **Not scored as Qari.** We build our own conversion from official weights (§4) |
| **All proprietary API-only models**: Gemini (all), GPT-5.x / GPT-4o, Claude, `qwen/qwen3.7-*`, `qwen/qwen3.8-max*`, `qwen/qwen4-max`, `mistral-ocr`, OpenRouter `cloudflare-ai` parser | No downloadable weights / external service: **excluded by the self-hosting requirement** (SHM §3) |
| MinerU2.5 | AGPL-3.0 (Class B): only with user approval |
| Qwen2.5-VL-3B / 72B | `qwen-research` (non-commercial) / custom `qwen` licence (Class C) |

## 3. OpenRouter as an optional test endpoint (eligible models only)

OpenRouter is **not** a candidate source. It may serve an eligible open-weight model for a quick, **indicative** comparison before self-hosting it: `qwen/qwen3-vl-8b-instruct`, `qwen/qwen3-vl-30b-a3b-instruct`, `qwen/qwen3-vl-235b-a22b-instruct`, `qwen/qwen3.5-27b`, `qwen/qwen3.6-27b`, `google/gemma-4-31b-it`, `mistralai/mistral-small-3.2-24b-instruct`, `z-ai/glm-4.6v` (all in the 2026-11-16 catalog). Rules:
- The OpenRouter ID is mapped to the HF repo + revision in the model registry. If the mapping is uncertain, the run is not counted at all.
- Fixtures and non-sensitive documents only by default; real company documents only with the user's explicit per-run approval.
- Results are labelled **"indicative (third-party serving)"** and excluded from ranking. Ranking uses self-hosted runs of the same weights.
- Useful for upper-bound models too large for the available hardware (e.g. Qwen3-VL-235B). This shows what capacity would buy, before the company sizes hardware.

## 4. CPU/GPU feasibility assessment and execution paths

**Estimates [ESTIMATE] below must be replaced by measurements in E2. Peak memory is measured, not assumed.**

| Candidate | CPU path on this laptop | Est. RAM | Feasible here? | GPU path | Recommended plan |
|---|---|---|---|---|---|
| Qari 0.4.0 (official adapter + base) | transformers + peft on CPU | bf16 ≈ 8.9 GB weights + activations; if CPU upcasts to fp32 ≈ 17.8 GB | **At risk.** Likely out of memory in fp32, and very slow in bf16 on AVX2 | Fits a 16 GB GPU in bf16 | **(A) Reference run:** official adapter + base on a cloud GPU (T4/L4 16–24 GB), bf16, prompt `Free OCR.`. **(B) Local run:** merge the adapter into the base ourselves (`peft.merge_and_unload`), convert to GGUF Q8_0 (and Q4_K_M) with llama.cpp's converter, then run with llama.cpp on CPU. **(B) is scored only after it matches (A) within ±0.01 CER** on ≥ 10 pages |
| Qari v0.3 2B | transformers CPU, bf16/fp32 | fp32 ≈ 8.8 GB | Yes (slow) | Any ≥ 8 GB GPU | Run locally. Cloud GPU optional for speed |
| Qari 0.2.2.1 | Adapter trained on a bitsandbytes-4bit base → bnb 4-bit needs CUDA | — | **Blocked as published** | Cloud GPU with CUDA | (A) cloud GPU with the published 4-bit base. (B) local: adapter on the unquantized `Qwen/Qwen2-VL-2B-Instruct`, recorded as a deviation and validated against (A) |
| PaddleOCR-VL 1.6 | Official GGUF via llama.cpp; or the PaddleOCR pipeline with CPU `paddlepaddle` | ≈ 2–4 GB | Yes | `paddlepaddle-gpu` (CUDA) | Run **both** the VL model alone (GGUF) and the full PaddleOCR document pipeline (layout + VL) on CPU. The pipeline matters for multi-column reading order |
| Nuqta 4B | Official GGUF Q4_K_M / Q8_0 | ≈ 4–7 GB | Yes (vendor: ~2.5 min/page) | vLLM, 16 GB | Local GGUF Q8_0 (accuracy-first) and Q4_K_M |
| dots.ocr | `ggml-org` GGUF via llama.cpp | ≈ 4–7 GB | Probably | vLLM / flash-attn | Try the GGUF; if it fails, cloud GPU or a documented blocker |
| AIN-7B | — | bf16 ≈ 16.6 GB > RAM | **No** | 24 GB GPU (or GGUF if available) | Cloud GPU, or a documented blocker |
| DeepSeek-OCR | CUDA-only per card | — | **No** | CUDA GPU | Optional cloud GPU |
| Tesseract | Native | < 1 GB | Yes | — | Local |

**Practical alternatives when local hardware is insufficient** (each needs the user's explicit approval, because documents leave the machine):
1. **Rented or free cloud GPU notebook/VM** (e.g. Kaggle/Colab T4 16 GB, or a paid L4/A10 24 GB instance). The same lab worker runs there. Only the selected evaluation pages are uploaded, and the user confirms which. Instance deletion is part of the run checklist.
2. **Intel iGPU acceleration:** llama.cpp Vulkan or SYCL builds on Iris Xe may speed up the GGUF paths. Optional, and measured against the CPU build.
3. **A smaller official variant** (Nuqta 0.8B, Qari v0.3 2B), only as an *addition*, never as a silent substitute for a blocked candidate.

## 5. Download and installation safety (requirements 5 and 7)

1. **Before any download**, the lab's model manager shows and records, per model: repo ID, **pinned revision (commit hash)**, licence (from the HF API and the LICENSE file), total download size, required runtime and dependencies, and hardware path. The user approves each download explicitly. Nothing downloads in tests or CI.
2. **Location outside Git:** `LAB_MODELS_DIR` (default `D:\agenticdoc-models`, since D: has the most free space; configurable), with `HF_HOME` / `HF_HUB_CACHE` pointed inside it. Root `.gitignore` adds `*.gguf`, `*.safetensors`, `*.bin`, `*.pdparams`, `**/models/`, `**/agenticdoc-models/`. A test asserts that no file > 10 MB is tracked under `Project sdaia/lab/`.
3. **Integrity:** sha256 of every downloaded file is stored in `models.lock.json`, which is committed and contains no weights. Conversions we build (Qari GGUF) record the source revisions, converter version and output hashes.
4. **Remote code:** paths that need `trust_remote_code=True` (some transformers paths for PaddleOCR-VL, dots.ocr, DeepSeek-OCR) are used only at a pinned revision whose Python files Codex has listed in the report, and Claude has reviewed. llama.cpp GGUF paths, which execute no repo code, are preferred.
5. **Runtimes:** llama.cpp prebuilt release binaries (official `ggml-org/llama.cpp` GitHub releases, CPU/AVX2 and optionally Vulkan) at a pinned tag with recorded hash. Heavy Python stacks (torch/transformers/peft, paddle) go in **separate virtual environments** (`lab-ocr-torch`, `lab-ocr-paddle`), so E1's dependencies stay untouched and paddle/torch conflicts are avoided.
6. **No user documents or generated sensitive content in Git:** OCR outputs live in the temporary lab workspace. Only synthetic-fixture results and aggregate reports may be committed, and only by explicit export.

## 6. Evaluation protocol (requirements 3 and 4)

### 6.1 Identical inputs and verified reference
- Inputs are E1 `ComparisonSet`s, reused unchanged: same document sha256, same pages, same **verified** ground truth versions. Every candidate, local and cloud, is scored inside the same set.
- Page images: rendered once per (page, DPI) and stored with their sha256. Every candidate receives the **identical image bytes**. Candidate-specific preprocessing (e.g. Nuqta's 2.4 MP resize) is a recorded, separately reported variant, never a hidden change.
- Test material: (a) the user's real Arabic documents (native PDFs rendered to images, plus real scans); (b) E1 fixtures rendered at 300/200/150 DPI with light noise and skew; (c) the E1 "E2 candidate" pages; (d) optionally public sets, with **contamination flags**: KITAB-Bench overlaps Nuqta's training data (its card says so), and Qari's own datasets overlap Qari. Results on contaminated sets are shown separately and never used for ranking.

### 6.2 Metrics

| Metric | Definition | GT needed |
|---|---|---|
| CER / WER | As E1 (LAB §8), NFC, diacritics kept; CER-no-diacritics secondary | Verified page text |
| Arabic reading order | GT gives the page as ordered lines/blocks. Output lines are matched to GT lines by best normalized-edit-distance alignment (threshold 0.5). **Kendall τ** over matched order, plus the share of GT lines matched | Verified text with line order (GT editor marks line breaks; ordered blocks for multi-column pages) |
| Numeric accuracy | E1 numeric recall/precision (exact, digit form preserved), plus a value-equivalent recall (same value, any digit script), reported separately | Verified |
| Table-text accuracy | CER and numeric recall restricted to text inside GT table regions. Table *structure* is E3 | GT with table regions marked (simple text-region marking in the GT editor) |
| Latency | Per page, wall time from image in to text out, **excluding model load**. Model load/warm-up reported separately. Median and p90 over ≥ 3 runs on ≥ 10 pages | — |
| Peak RAM / VRAM | Worker process peak RSS (psutil sampling at 100 ms plus OS peak working set); VRAM via `torch.cuda.max_memory_allocated` or `nvidia-smi` sampling on GPU paths; "n/a (CPU)" otherwise | — |
| Cost | API: actual usage / cost from responses (`cost_source`). Cloud GPU: instance $/h × measured time. Local: $0 with hardware stated; energy not measured | — |
| Failure rate | Pages with error, timeout, empty, or runaway output (repetition loop > 2× GT length) | — |
| Hallucination signals | Output numbers absent from GT (numeric precision); inserted text spans (E1 error inspection) | Verified |

All E1 error-inspection features (individual errors, categories, number check list) apply to every E2 candidate.

### 6.3 Fairness rules
- Each candidate uses its **documented** prompt and settings (e.g. Qari `Free OCR.`, PaddleOCR-VL `OCR:`, Nuqta greedy, `enable_thinking=False`). One additional common prompt is reported separately for VLMs. Settings are recorded and versioned.
- Decoding: temperature 0, or greedy, everywhere it is supported. `max_new_tokens` ≥ 2× GT tokens.
- Quantized or converted variants are labelled with quantization and source. They are scored as the original only if validated against the original (±0.01 CER on ≥ 10 pages).
- A candidate's result counts only on pages where its run completed. Coverage (completed pages / total) is shown next to every score. A blocked candidate shows "blocked: <reason>" instead of a score.

## 7. Outputs and decision process (requirement 10)
1. `docs/architecture/E2_OCR_RESULTS.md`, generated from Lab exports and holding aggregates only (no document text): per-candidate metrics per ComparisonSet, breakdowns by page tag, DPI and producer, latency and resources, cost, coverage, blockers.
2. A Lab "E2 comparison" view where the user inspects, for any page: the image and each candidate's output side by side, and the individual errors.
3. Claude writes a **non-binding analysis** (strengths, risks, uncertainty, what more data would change the ranking). **No OCR solution is selected until the user has reviewed the results personally and recorded the decision** in `docs/reviews/CLAUDE_REVIEW.md` (user decision entry). E5 starts only after that.

## 8. Risks
- **Contradictory vendor claims** (Qari 0.122 vs third-party 0.64 CER). Mitigation: independent measurement on our verified sets. Neither claim is used in the decision.
- **Domain mismatch:** Qari 0.4 targets Islamic printed books, while our documents may be modern reports. Mitigation: page tags and per-domain breakdowns.
- **CPU-only latency:** 4B models at minutes per page. Mitigation: small verified sets (e.g. 30–60 pages) for local paths, with cloud GPU for scale if approved.
- **Conversion drift** from self-built GGUF. Mitigation: validation against the reference run (§6.3).
- **Supply chain** (remote code, binaries). Mitigation: pinned revisions, hashes, code review (§5).
