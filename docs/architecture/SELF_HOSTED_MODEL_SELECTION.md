# AgenticDoc — Self-Hosted Model Policy & Candidate Comparison

**Author:** Claude · **Date:** 2026-11-16 · **Status:** Mandatory policy (user requirement). **This supersedes the OpenRouter-first model selection** in MODEL_RESEARCH §1, §4–§9 and TECHNICAL_DESIGN §11.
**Clarification (2026-11-16):** the model must be downloadable, self-hostable and suitably licensed, but **it does not have to run locally during evaluation**. OpenRouter and Hugging Face are permitted *evaluation providers* (§1a), never production dependencies.
**Requirement:** every AI model evaluated for potential production use must have publicly downloadable weights and a usable inference implementation, and be self-hostable on a private company server. The production system must be able to run entirely inside company infrastructure without sending documents to external AI services. **No model becomes the production default until the user has personally inspected and approved the comparison results.**

**Evidence and method.** Licence fields, gating, parameter counts and licence-file presence come from the Hugging Face API (`/api/models/{id}`), fetched 2026-11-16 for ~75 repositories. Licence texts and model cards were read where they carry the actual terms. **Nothing was downloaded.** RAM/VRAM numbers are [ESTIMATE]: bf16 weights ≈ params × 2 bytes, plus activations/KV cache. They must be replaced by measurements in the E-phases. **This is a technical licence screening, not legal advice:** the company's legal team must sign off before any model goes into production.

---

## 1. Eligibility rules

| Class | Meaning | Treatment |
|---|---|---|
| **A** | OSI-approved permissive licence (Apache-2.0, MIT, BSD), with the licence text present in the model repo, **and** every upstream base model also Class A | Eligible |
| **A-tag** | Permissive licence declared **only by the HF metadata tag** (no LICENSE file in the model repo), base chain permissive | Eligible for evaluation. Licence text must be confirmed (upstream code repo, official page, or written confirmation from the publisher) **before production** |
| **B** | Downloadable, but the terms are custom, copyleft or carry extra conditions (e.g. a custom agreement on top of MIT, AGPL-3.0, vendor "open model" licences, a "community" licence) | Evaluate only if the user approves. Never the production default without legal sign-off |
| **C** | Non-commercial, research-only, gated custom terms, user-count/field-of-use restrictions, **or API-only (no weights)** | **Excluded** |

Additional rules:
1. **Open weights ≠ open source** (user rule 4). The tag is a claim, not the licence. Derived models inherit obligations from their base, so the whole chain is checked (e.g. a fine-tune tagged Apache-2.0 on a restrictively licensed base is not Class A).
2. **Pin a revision.** A licence verdict applies to a specific commit. A re-check is required when moving to a new revision.
3. **Residual risks outside this screening:** training-data provenance, export-control and sector rules, and acceptable-use clauses. These are for legal review.
4. ~~OpenRouter only as an indicative test endpoint; final scores only from self-hosted inference.~~ **Superseded 2026-11-16 by the user's clarification, see §1a.** Hosted and local evaluations are both eligible when the exact model meets the downloadable/self-hostable/licensing requirements.

## 1a. Evaluation providers (user clarification, 2026-11-16)
**Principle:** the *model* must be downloadable, self-hostable and suitably licensed (classes in §1). The *evaluation* does not have to run locally. Production stays fully self-hosted (TD §0).

| # | Rule |
|---|---|
| 1 | **Eligibility first.** Only Class A/A-tag models (Class B with user approval). **API availability is never evidence** that a model is open, downloadable or self-hostable. API-only proprietary models stay excluded (§3). |
| 2 | **Provider preference for evaluation:** (a) **OpenRouter** or **Hugging Face Inference Providers** when the *exact* eligible model is served; (b) otherwise **local** inference when hardware and dependencies permit; (c) otherwise an approved private/rented GPU (SHM §5a.4). |
| 3 | **Ranking:** results from OpenRouter, Hugging Face or local inference are **all eligible for ranking**, as long as the model identity is verified (rule 4). Every result records its `inference_source` ∈ {`openrouter`, `huggingface`, `local`, `private_gpu`}, and reports show it next to every score. |
| 4 | **Identity and settings verification per hosted run:** (i) the provider's model must map to the registry's HF repo. OpenRouter exposes `hugging_face_id` (e.g. `qwen/qwen3-vl-8b-instruct` → `Qwen/Qwen3-VL-8B-Instruct`, verified 2026-11-16); HF Inference uses the repo ID directly. (ii) Record the **serving provider** and **quantization/precision** from OpenRouter's `/models/{id}/endpoints` (e.g. Parasail, bf16) or the HF provider mapping. (iii) **Pin the provider** for a comparison set (OpenRouter `provider.order` + `allow_fallbacks: false`), so one set isn't served by mixed backends. (iv) Hosted APIs don't expose the HF commit. Record `revision: provider-unspecified` + the run date, and flag the result if the HF repo changed afterwards. (v) Record decoding settings, image size limits and any provider-side image resizing. |
| 5 | **Cross-source consistency (when feasible):** if a hosted and a local run of the same model are both available, compare them on a shared sample. A CER difference > 0.02 is flagged as a possible provider modification (quantization or preprocessing), and both numbers are reported. |
| 6 | **Latency, cost and hardware:** hosted latency and cost are reported but labelled **"hosted — not indicative of self-hosted performance."** Self-hosted hardware needs come from model specifications and local measurements where available (§5, §5a.2). They are never inferred from API latency. |
| 7 | **Approvals:** no paid API call, no large weight download, and no GPU rental without explicit user approval (per run or per budget). Free hosted endpoints still count as external transfer. |
| 8 | **Documents sent to hosted providers:** synthetic fixtures by default. Real or company documents only with explicit user approval per document set, with OpenRouter `provider.data_collection: "deny"` (and `zdr` where available). Third-party retention is documented separately from local deletion. |
| 9 | **Production:** unchanged. The approved model runs on company infrastructure through the inference gateway (TD §0), with no external inference service. Hosted providers are **evaluation providers only**, never production dependencies. |
| 10 | **Configurability:** model weights (repo + revision), serving backend, base URL and provider are configuration. The same registry entry can point to OpenRouter/HF during evaluation and to an internal vLLM/llama.cpp/TEI server in production. |

**Hosted availability snapshot (2026-11-16):**
- **OpenRouter** serves the eligible Qwen3-VL (8B / 30B-A3B / 235B), Qwen3.5/3.6, Qwen3-32B / 30B-A3B, Gemma 4, Mistral Small 3.2, gpt-oss, GLM-4.6V, Qwen3-Embedding 4B/8B, bge-m3, multilingual-e5-large and Qwen3-Reranker 0.6B/8B.
- **HF Inference Providers:** Qwen3-VL-8B (featherless-ai: live; novita: error) and Qwen3-Embedding-8B (deepinfra, scaleway).
- **Not hosted anywhere checked:** Qari-OCR (all versions), PaddleOCR-VL 1.6, Nuqta. These require local or approved-GPU evaluation.

## 2. Candidate comparison

Notation: **Lic** = class from §1. **VRAM bf16** [ESTIMATE] = weights only; real peak is higher. "CPU" = feasible on CPU (usually via GGUF/ONNX, slow for ≥ 4B). OR = available as an OpenRouter test endpoint in the 2026-11-16 catalog. All download sources are `https://huggingface.co/<id>` unless stated.

### 2.1 OCR and document-parsing models

| Model ID (version) | Licence & commercial terms | Lic | Size / VRAM bf16 | CPU / GPU | Languages | Arabic evidence | Install / inference | Private-server deployment |
|---|---|---|---|---|---|---|---|---|
| **NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct** (rev `aa65b4a4`, 2026-02-01) — **mandatory, priority** | Apache-2.0 tag; no LICENSE file; **publisher statement** (Qari-OCR Team, discussion #1): Apache 2.0 allows research and commercial use (see §2.1a). Adapter base `unsloth/Qwen3-VL-4B-Instruct` (Apache-2.0 tag) → `Qwen/Qwen3-VL-4B-Instruct` (Apache-2.0 tag; upstream `QwenLM/Qwen3-VL` has an Apache LICENSE file). Training dataset `seemorg/books-ocr`: MIT tag | **A-tag, publisher-confirmed** | LoRA 0.31 GB + base 4.44B → ≈ 9 GB; 12–16 GB GPU | GPU; CPU only via a self-built GGUF (merge + convert) | Arabic only | [VENDOR] CER 0.122 / WER 0.256 (unnamed set); third-party (Nuqta card) QARI CER 0.64 on Misraj-DocOCR | transformers + peft; vLLM with LoRA; llama.cpp after merge | vLLM OpenAI server (Docker) or llama.cpp server |
| **NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct** — **mandatory** | Apache-2.0 tag, no LICENSE file | A-tag | 2.21B → ≈ 4.4 GB | CPU (slow) / GPU ≥ 8 GB | Arabic | [VENDOR] CER 0.300 / WER 0.485; HTML/Markdown structure | transformers | vLLM / transformers worker |
| **NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct** — **mandatory** | Apache-2.0 tag; base `unsloth/Qwen2-VL-2B-Instruct-unsloth-bnb-4bit` Apache-2.0 tag | A-tag | adapter 0.12 GB + 2.25B (4-bit) | **CUDA** (bitsandbytes) | Arabic | [VENDOR] best raw-text CER 0.061 (per v0.3 card) | transformers + peft + bitsandbytes | GPU worker |
| **PaddlePaddle/PaddleOCR-VL-1.6** (rev 2026-11-06) — **mandatory** | Apache-2.0, **LICENSE file present**; base ERNIE-4.5-0.3B (check its licence file at kickoff) | A | 0.96B → ≈ 2 GB | CPU (Paddle CPU or official GGUF) / GPU | 109 languages incl. Arabic | [VENDOR] v1 Arabic edit distance 0.122; OmniDocBench SOTA claims | `paddleocr[doc-parser]`; vLLM backend; official GGUF `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` via llama.cpp | PaddleOCR serving / vLLM / llama.cpp Docker |
| **PaddleOCR PP-OCRv5**: `PaddlePaddle/PP-OCRv5_server_det` + **`PaddlePaddle/arabic_PP-OCRv5_mobile_rec`** (ONNX variant available) — **mandatory** | Apache-2.0 tag (PaddleOCR code repo Apache-2.0) | A-tag | tiny (< 0.1 GB) | **CPU** fine; ONNX Runtime without Paddle possible | Arabic-specific recognizer | KITAB-Bench measured *classic* PaddleOCR CER 0.79 (older version); v5 unmeasured | `paddleocr`, or ONNX Runtime | Any CPU container |
| **SalahALHaismawi/Nuqta-Arabic-OCR-4B** (rev 2026-10-27) | Apache-2.0, LICENSE present; base `Qwen/Qwen3.5-4B` Apache-2.0, LICENSE present | **A** | 4.75B → ≈ 9.5 GB; 16 GB GPU; GGUF Q4 2.9 GB / Q8 4.8 GB | CPU (official GGUF, vendor ~2.5 min/page) / GPU | Arabic (+ ID/MRZ) | [VENDOR] KITAB-Bench CER 0.106 (0.113 excluding 234 overlapping test images); Misraj CER 0.121 | transformers; vLLM; llama.cpp; `nuqta-ocr` pip | vLLM / llama.cpp Docker. Single-author project, a maintenance risk |
| SalahALHaismawi/Nuqta-Arabic-OCR-0.8B | Apache-2.0, LICENSE present | A | 0.89B | CPU / GPU | Arabic | none published | as above | as above |
| deepseek-ai/DeepSeek-OCR | MIT, LICENSE present | A | 3.34B → ≈ 6.7 GB | **CUDA** (flash-attn) | multilingual | none for Arabic | transformers / vLLM | GPU vLLM |
| MBZUAI/AIN | MIT tag, no LICENSE file; Qwen2-VL base | A-tag | 8.29B → ≈ 16.6 GB; 24 GB GPU | GPU | Arabic-English | KITAB-Bench CER 0.20 (cited by Nuqta) | transformers + qwen-vl-utils | GPU worker |
| ibm-granite/granite-docling-258M | Apache-2.0 tag | A-tag | 0.26B | CPU / GPU | multilingual (Arabic support to verify) | none | Docling (MIT) | CPU container. Mainly an E3 structure candidate |
| dots-studio/dots.ocr | **Custom "dots.ocr LICENSE AGREEMENT" on top of MIT**: commercial use and closed-source on-prem allowed; prohibited-use clause with *automatic termination*; "Built with dots.ocr" required for modified weights; **PRC law, Hangzhou arbitration**; unfilled fields | **B** | 3.04B → ≈ 6 GB | GPU (vLLM); GGUF CPU | 100 languages | Misraj CER 0.40 (cited by Nuqta) | vLLM / llama.cpp | Only with user approval and legal review |
| opendatalab/MinerU2.5-2509-1.2B | **AGPL-3.0** (copyleft, network clause) | **B** | 1.16B | GPU / CPU | multilingual | none | MinerU toolkit | Only with legal approval |
| allenai/olmOCR-2-7B-1025 | Apache-2.0 tag | A-tag | 8.29B | GPU | English-centric | none | vLLM | Low relevance for Arabic. Optional |
| Tesseract 5 + `ara` traineddata (GitHub `tesseract-ocr`) | Apache-2.0 | A | small | CPU | Arabic | KITAB-Bench CER 0.54 | apt / binaries | Floor baseline |

### 2.1a Qari-OCR licence verification (2026-11-16, user-supplied lead)
Source: https://huggingface.co/NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct/discussions/1

| Question | Finding | Evidence |
|---|---|---|
| Who answered? | The `Omartificial-Intelligence-Space` account (labelled the NAMAA org, "Network for Advancing Modern ArabicNLP & AI"), signed "Qari-OCR Team" | Discussion #1, replies dated Jul 19 and Jul 23 (no year shown) |
| What was stated? | "The Qari-OCR model is released under the Apache 2.0 license, which allows both research and commercial use," including fine-tuning, derivative models, adapters/weights and commercial integration, "subject to the terms of the Apache 2.0 license" | Reply 1 |
| Which version? | Posted on the **0.4.0** repo. The statement says "the Qari-OCR model" without a version. Treat it as covering 0.4.0. For v0.3 and 0.2.2.1, rely on their Apache-2.0 tags plus this statement until confirmed per version | Repo page |
| Pinned revision | `aa65b4a46336c6cc608e7da5a015f8e71472a68b` (lastModified 2026-02-01) | HF API |
| Base-model chain | `adapter_config.json` → `base_model_name_or_path: unsloth/Qwen3-VL-4B-Instruct` (Apache-2.0 tag), a re-upload of `Qwen/Qwen3-VL-4B-Instruct` (Apache-2.0 tag). Upstream code repo `QwenLM/Qwen3-VL` LICENSE = Apache License. **Discrepancy:** the card's tags name the Qwen original while the adapter config names the Unsloth copy. At download time, compare the Unsloth base's weight hashes with the Qwen original, and prefer the Qwen original if they're identical | HF API, adapter_config.json, GitHub |
| Training data | Card tags `seemorg/books-ocr` (MIT tag). The team **did not answer** the dataset-licence questions and said "we do not provide the full dataset." Rights in the underlying book scans are unknown | Reply 2; HF dataset API |
| Dependencies (inference) | transformers (Apache-2.0), peft (Apache-2.0), PyTorch (BSD-3), qwen-vl-utils (Apache-2.0, verify at install); vLLM (Apache-2.0) or llama.cpp (MIT) for serving. Unsloth is a *training* tool and isn't needed for inference | Package metadata (verify pinned versions at E2-A) |
| **Security** | The repo contains `training_args.bin`, a **Python pickle**. It must **never be loaded**: use safetensors only, and don't use `torch.load` on repo files | HF file list |
| Classification | **A-tag, publisher-confirmed**: eligible and a priority E2 candidate. **Production still requires legal sign-off** (residual risks: no LICENSE file, no version in the statement, unanswered training-data rights) | — |

### 2.2 Vision-language models (OCR, charts, tables, Stage-2 visual analysis)

| Model ID | Licence | Lic | Params / VRAM bf16 | Deploy notes | Arabic evidence | OR |
|---|---|---|---|---|---|---|
| **Qwen/Qwen3-VL-2B / 4B / 8B / 32B-Instruct** | Apache-2.0 tag (no LICENSE file in model repos) | A-tag | 2.1B / 4.4B / 8.8B (≈ 18 GB) / 33.4B (≈ 67 GB) | vLLM, transformers, llama.cpp GGUF | Qwen3-VL-4B CER 0.49 and 8B CER 0.69 on Qari's own set (vendor of a competing model) | 8B: yes |
| **Qwen/Qwen3-VL-30B-A3B-Instruct** (MoE, 3B active) | Apache-2.0 tag | A-tag | 31B total (≈ 62 GB) | vLLM; fast for its size | none | yes |
| Qwen/Qwen3-VL-235B-A22B-Instruct | Apache-2.0 tag | A-tag | 236B (≈ 470 GB; multi-GPU) | Upper bound only, needs a large GPU cluster | none | yes |
| **Qwen/Qwen3.8-27B** (rev 2026-11-07; image-text-to-text) | Apache-2.0, **LICENSE present** | **A** | 27.8B (≈ 56 GB; 4-bit ≈ 16 GB) | vLLM | none | not in catalog |
| Qwen/Qwen3.6-27B, Qwen3.6-35B-A3B, Qwen3.5-9B / 27B / 35B-A3B | Apache-2.0, LICENSE present | A | 9.7–36B | vLLM (verify image support per model card at kickoff) | none | yes |
| **google/gemma-4-31b-it**, gemma-4-26b-a4b-it | Apache-2.0 tag; card links a Gemma 4 licence page (**confirm it is plain Apache-2.0 with no prohibited-use policy**); no LICENSE file | A-tag | 31.3B (≈ 63 GB) / 25.8B MoE | vLLM, llama.cpp | 140+ languages (Arabic not named); OmniDocBench 1.5 edit distance 0.131 [VENDOR] | yes |
| mistralai/Mistral-Small-3.2-24B-Instruct-2506 | Apache-2.0 tag | A-tag | 24B (≈ 48 GB) | vLLM | `ar` listed | yes |
| openbmb/MiniCPM-V-4_5 | Apache-2.0 (card: weights and code; registration optional) | A-tag | 8.7B (≈ 17 GB) | vLLM, llama.cpp, Ollama | 30+ languages (Arabic not named); OCRBench claims [VENDOR] | — |
| OpenGVLab/InternVL3_5-8B | Apache-2.0 tag | A-tag | 8.5B | vLLM, lmdeploy | none | — |
| zai-org/GLM-4.6V | MIT tag | A-tag | 108B MoE (multi-GPU) | vLLM | none | yes |

### 2.3 Embedding models

| Model ID | Licence | Lic | Params / memory | Context | Languages / Arabic | Serving |
|---|---|---|---|---|---|---|
| **Qwen/Qwen3-Embedding-0.6B / 4B / 8B** | Apache-2.0 (8B: LICENSE present; 0.6B/4B: tag) | A / A-tag | 0.6B (CPU OK) / 4B / 7.6B (≈ 15 GB, GPU) | 32k | 100+ languages; MMTEB #1 (70.58, 2025-06-05) [VENDOR] | vLLM pooling, HF TEI, sentence-transformers. OR: 4B, 8B |
| **BAAI/bge-m3** | MIT tag | A-tag | 568M (CPU OK) | 8k | 100+ languages; dense + sparse + multi-vector (supports hybrid retrieval natively) | TEI, FlagEmbedding. OR: yes |
| intfloat/multilingual-e5-large-instruct | MIT tag | A-tag | 560M | **512** | Arabic listed | TEI |
| Alibaba-NLP/gte-multilingual-base | Apache-2.0 tag | A-tag | 305M | 8k | Arabic listed | TEI (`trust_remote_code`) |
| Snowflake/snowflake-arctic-embed-l-v2.0 | Apache-2.0 tag | A-tag | 568M | 8k | Arabic listed | TEI |
| ibm-granite/granite-embedding-278m-multilingual | Apache-2.0 tag | A-tag | 278M | verify | Arabic listed | TEI |
| Omartificial-Intelligence-Space/GATE-AraBert-v1 | Apache-2.0 tag | A-tag | 135M | 512 | **Arabic only** (no cross-lingual) | sentence-transformers |

### 2.4 Rerankers

| Model ID | Licence | Lic | Params | Notes |
|---|---|---|---|---|
| **Qwen/Qwen3-Reranker-0.6B / 4B / 8B** | Apache-2.0 tag | A-tag | 0.6B / 4B / 8.2B | 32k; vLLM score API. OR: 0.6B, 8B |
| **BAAI/bge-reranker-v2-m3** | Apache-2.0 tag | A-tag | 568M | CPU OK; TEI |
| mixedbread-ai/mxbai-rerank-large-v2 | Apache-2.0, LICENSE present | A | 1.54B | `ar` listed |
| Alibaba-NLP/gte-multilingual-reranker-base | Apache-2.0 tag | A-tag | 306M | `ar` listed; TEI |
| NAMAA-Space/GATE-Reranker-V1 | Apache-2.0 tag | A-tag | 135M | Arabic only, 512 tokens, unreadable published metrics |

### 2.5 Chatbot / generation LLMs

| Model ID | Licence | Lic | Params / VRAM bf16 | Arabic relevance | OR |
|---|---|---|---|---|---|
| **Qwen/Qwen3-8B / 14B / 32B**, **Qwen3-30B-A3B-Instruct-2507** | Apache-2.0, LICENSE present | A | 8.2B (≈ 16 GB) / 14.8B / 32.8B / 30.5B MoE | multilingual, Arabic included per Qwen claims (to measure) | 32B, 30B-A3B |
| **Qwen/Qwen3.8-27B**, Qwen3.6-27B / 35B-A3B, Qwen3.5-9B / 27B | Apache-2.0, LICENSE present | A | 9.7–36B | to measure | 3.5/3.6 yes |
| **humain-ai/ALLaM-7B-Instruct-preview** | Apache-2.0 tag, no LICENSE file | A-tag | 7B (≈ 14 GB) | **Arabic-first** (Saudi). Verify context length at kickoff (it may be short for RAG) | — |
| inceptionai/jais-family-13b-chat | Apache-2.0 tag | A-tag | 13.5B | Arabic-first; 2024 release; verify context length | — |
| QCRI/Fanar-1-9B-Instruct | Apache-2.0 tag | **A-tag, base chain to verify**: Fanar-1-9B is reported to be continually pre-trained from a Gemma-family base. If so, Gemma terms may flow down and it becomes Class B/C | 8.8B | Arabic-first | — |
| **openai/gpt-oss-20b / 120b** | Apache-2.0, LICENSE present; `USAGE_POLICY` only asks for compliance with applicable law (no extra restrictions) | **A** | 20.9B (MXFP4 ≈ 16 GB) / 116.8B (≈ 65 GB MXFP4, single 80 GB GPU) | Arabic quality unknown. **Open-weight, self-hostable; unrelated to the excluded GPT APIs** | yes |
| google/gemma-4-31b-it / 26b-a4b-it | Apache-2.0 tag (confirm licence page) | A-tag | 31.3B / 25.8B MoE | 140+ languages | yes |
| mistralai/Mistral-Small-3.2-24B-Instruct-2506 | Apache-2.0 tag | A-tag | 24B | `ar` listed | yes |
| deepseek-ai/DeepSeek-V3.2 | MIT, LICENSE present | A | 685B (multi-node) | Eligible but outside realistic server sizing | — |

## 3. Previously proposed models that are now excluded

| Previously proposed (where) | Role | Why excluded | Replacement candidates |
|---|---|---|---|
| `openai/gpt-4o-mini` (current code, MODEL_RESEARCH §9) | Generation | API-only, no weights (Class C) | Qwen3/3.5/3.6/3.8, ALLaM-7B, Gemma 4, gpt-oss, Mistral Small 3.2 |
| `openai/text-embedding-3-small` (current code) | Embeddings | API-only | Qwen3-Embedding, bge-m3, others in §2.3 |
| `google/gemini-3.1-flash-lite`, `gemini-3.7-flash`, `gemini-3.1-pro-preview` (MODEL_RESEARCH §4, §9; E2 plan §3) | Vision, OCR | API-only | Qwen3-VL, Qwen3.8-27B, Gemma 4, OCR models in §2.1 |
| `openai/gpt-5.6-luna`, `anthropic/claude-haiku-5.5`, other GPT/Claude/Grok | Generation / vision | API-only | as above |
| `qwen/qwen3.7-flash`, `qwen/qwen3.7-plus`, `qwen/qwen3.8-max*`, `qwen/qwen4-max` (OpenRouter IDs) | Vision / generation | **No downloadable weights** for these IDs (HF search of Qwen org: no Qwen3.7 or Qwen4 repos) | Downloadable Qwen3.5/3.6/3.8-27B, Qwen3-VL |
| `mistral-ocr` engine, `cloudflare-ai` parser (OpenRouter file-parser) | PDF OCR / parsing | External hosted services, not self-hostable | PaddleOCR-VL, PP-OCRv5, Qari, Nuqta |
| `cohere/rerank-*`, `mongodb/rerank-*` (Voyage) | Reranking | API-only | Qwen3-Reranker, bge-reranker-v2-m3, mxbai-rerank |
| `google/gemini-embedding-2`, `cohere/embed-5-*`, `mongodb/voyage-4*` | Embeddings | API-only | §2.3 |
| `nvidia/nemotron-3.5-embed/rerank:free` (seen in catalog) | Embeddings / rerank | Licence and weights not verified; free-tier retention unknown | Re-check only on request (likely Class B, vendor licence) |

Downloadable models excluded on **licence** grounds (they would otherwise have been plausible candidates):

| Model | Licence found | Class |
|---|---|---|
| Qwen/Qwen2.5-VL-3B-Instruct | `qwen-research` (non-commercial research) | C |
| Qwen/Qwen2.5-VL-72B-Instruct | custom `qwen` licence (usage-size conditions) | C (B only with legal approval) |
| Qwen/Qwen3.8-Flash-Next | custom `qwen-community-1.0` | B → excluded unless legal approves |
| Qwen/Qwen3.8-2.4T-A95B | custom `qwen3.8-max` | B/C, and impractical size |
| google/gemma-3-27b-it, gemma-3-12b-it, embeddinggemma-300m | Gemma Terms of Use, gated | C |
| meta-llama/Llama-4-Scout, Llama-3.3-70B | Llama community licences + use policy (gated) | C |
| jinaai/jina-embeddings-v3, jina-reranker-v2-base-multilingual | CC-BY-NC-4.0 | C |
| CohereLabs/c4ai-command-r7b-arabic-02-2025 | CC-BY-NC-4.0 (gated) | C |
| tiiuae/Falcon-H1-7B-Instruct | custom Falcon LLM licence | B → excluded unless legal approves |
| Baseer / Baseer v2 (Misraj) | weights not public (HTTP 401) | C |
| Surya | gated (401) | C |

Still eligible but **deprioritized**: Qwen3-VL-235B, GLM-4.6V and DeepSeek-V3.2 (eligible, but they need a GPU cluster); olmOCR-2 (English-centric).

## 4. Self-hosted serving stack (all open source)

| Component | Licence | Serves | Private-server option |
|---|---|---|---|
| vLLM | Apache-2.0 | VLMs, LLMs, embeddings (pooling), rerankers (score), LoRA adapters; OpenAI-compatible API | Official `vllm/vllm-openai` Docker image (CUDA). Disable usage stats (`VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1`) |
| llama.cpp `llama-server` | MIT | GGUF models on CPU, CUDA or Vulkan; OpenAI-compatible API | Official `ggml-org/llama.cpp` server images or release binaries |
| HF Text Embeddings Inference (TEI) | Apache-2.0 | Embeddings and rerankers (bge, gte, Qwen3-Embedding where supported) | Official CPU and GPU images |
| PaddleOCR / PaddleX serving | Apache-2.0 | PP-OCRv5, PaddleOCR-VL pipeline | Paddle Docker images; ONNX Runtime for PP-OCRv5 |
| Tesseract | Apache-2.0 | Baseline OCR | OS package |

Image names, tags and CUDA versions are verified and pinned at implementation time. **Air-gapped operation:** weights are mirrored to an internal artifact store with recorded sha256, `HF_HUB_OFFLINE=1` is set, and an egress firewall allows the inference hosts only.

## 5. Hardware profiles [ESTIMATE — to be measured]

| Profile | Example | Fits (bf16 unless noted) |
|---|---|---|
| **P0: current evaluation laptop** | i7-1255U, 15.7 GB RAM, **no NVIDIA GPU** | CPU only: PP-OCRv5, Tesseract, PaddleOCR-VL GGUF, Nuqta GGUF, Qari v0.3 (slow), bge-m3, Qwen3-Embedding-0.6B, bge-reranker-v2-m3; LLMs ≤ 8B in Q4 GGUF (slow) |
| **P1: single 24 GB GPU server** | L4 / A10 / RTX 4090 class, 64 GB RAM | All OCR models in §2.1; Qwen3-VL-8B, MiniCPM-V 4.5, InternVL3.5-8B; Qwen3-Embedding-8B + Qwen3-Reranker-4B; LLMs ≤ 14B bf16, or 27–32B in 4-bit (AWQ/GPTQ), gpt-oss-20b |
| **P2: single 80 GB GPU** (or 2 × 48 GB) | H100 / A100 80 GB / 2 × L40S | Qwen3.8-27B, Qwen3.6-27B, Gemma-4-31B, Qwen3-VL-30B-A3B / 32B in bf16; gpt-oss-120b (MXFP4) |
| **P3: multi-GPU cluster** | ≥ 4 × 80 GB | Qwen3-VL-235B, GLM-4.6V, DeepSeek-V3.2 |

**Required input from the user:** the target company server specification (GPU model and count, VRAM, RAM, CPU, OS, Docker/Kubernetes, air-gapped or not). Final candidate ranking must report results **per hardware profile the company can actually provide.**

## 5a. User decisions (2026-11-16)
1. **The OpenRouter PDF parser is removed from E1-D.** AC-E1.15h/16 are superseded. The E1 lab makes no network calls.
2. **No company server specification is available yet.** Evaluations must not assume one. Every run records **measured** RAM and VRAM, the actual hardware used (CPU, GPU model, driver, OS), and a reproducible deployment configuration: model ID + revision, weight hashes, serving stack + version, container image + tag or exact install commands, launch flags, and quantization. Hardware profiles in §5 are planning aids, not assumptions.
3. **dots.ocr and MinerU are research candidates** (licence research, published evidence). **Don't install or run** them, or any model with an unresolved or incompatible licence, without the user's explicit approval for that model.
4. **Local GPUs and private or rented GPU environments may be considered** for evaluation. **No rental costs** and **no transfer of documents to external infrastructure** without explicit user approval each time (which documents, which provider, estimated cost).
5. **Legal approval is required before any production deployment** of any model, including Class A.

## 6. Evaluation rules under the self-hosting policy
1. Only Class A / A-tag candidates by default; Class B only with explicit user approval per model.
2. All candidates are scored on the **identical verified Arabic test documents** (E1 ComparisonSets) with byte-identical inputs.
3. **Scored runs may use any eligible evaluation provider** (§1a): OpenRouter, Hugging Face Inference Providers, local inference, or an approved private/rented GPU. Each result records its `inference_source`, provider, quantization and settings. Hosted runs use fixtures by default (§1a rule 8).
4. Per candidate, the report includes: exact ID + revision, download source, licence class + evidence, hardware profile used, measured peak RAM/VRAM, latency, accuracy metrics (per E2/Phase 4/Phase 5 criteria), and coverage.
5. **No production default** until the user has reviewed and approved the results (decision recorded in CLAUDE_REVIEW).

## 7. Sources
Hugging Face model pages `https://huggingface.co/<id>` for every ID above, and `https://huggingface.co/api/models/<id>` (metadata snapshot 2026-11-16); dots.ocr licence: `https://huggingface.co/dots-studio/dots.ocr/blob/main/dots.ocr%20LICENSE%20AGREEMENT`; gpt-oss usage policy: `https://huggingface.co/openai/gpt-oss-20b/blob/main/USAGE_POLICY`; Gemma 4 card: `https://huggingface.co/google/gemma-4-31b-it`; MiniCPM-V 4.5 card: `https://huggingface.co/openbmb/MiniCPM-V-4_5`; Nuqta GGUF card: `https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B-GGUF`; PaddleOCR-VL 1.6 GGUF: `https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF`; OpenRouter catalog `https://openrouter.ai/api/v1/models` (2026-11-16).
