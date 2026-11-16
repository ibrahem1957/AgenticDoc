# AgenticDoc — Repository Audit

**Author:** Claude (Lead Architect / Reviewer) · **Date:** 2026-11-16 · **Commit audited:** `c0a4f5a` (branch `main`)
**Method:** Full static read of every tracked source file. No code was executed against the API (no `OPENROUTER_API_KEY` available in the audit environment). Items marked **CONFIRMED** are visible directly in the code; items marked **RISK** are plausible failure modes that depend on runtime conditions.

---

## 1. Repository inventory

All production code lives under `Project sdaia/src/` (541 lines total including the 95-line sample `data.txt`).

| File | Lines | Role |
|---|---|---|
| `Project sdaia/src/main.py` | 75 | CLI entry point: index → summarize → generate questions → chat loop |
| `Project sdaia/src/agent/base.py` | 131 | Custom ReAct engine (`BaseAgent`) |
| `Project sdaia/src/agent/prompts.py` | 42 | `SUMMARIZER_PROMPT`, `QUESTION_GENERATOR_PROMPT` |
| `Project sdaia/src/chatbot/chat.py` | 55 | `ChatBot` (RAG question answering) |
| `Project sdaia/src/llm/openrouter.py` | 32 | `OpenRouterLLM` chat-completions wrapper |
| `Project sdaia/src/rag/chunker.py` | 9 | Fixed-size character chunker |
| `Project sdaia/src/rag/embeddings.py` | 21 | `OpenRouterEmbeddings` |
| `Project sdaia/src/rag/vector_store.py` | 36 | In-memory cosine-similarity store |
| `Project sdaia/src/rag/rag_pipeline.py` | 20 | `RAGPipeline` (build_index / retrieve) |
| `Project sdaia/src/tools/file_tool.py` | 5 | `read_file` tool |
| `Project sdaia/src/tools/registry.py` | 4 | `TOOLS` dict |
| `Project sdaia/src/observability/observe.py` | 16 | `@observe` timing decorator |
| `Project sdaia/src/data.txt` | 95 | Sample English story (only test input) |
| `README.md` | 149 | Project description |

**Missing entirely:** `requirements.txt` / `pyproject.toml`, `.gitignore`, `.env.example`, tests, any PDF/image handling, any API server. `__pycache__/*.pyc` (CPython 3.13) files are committed.

**How it runs today:** `main.py` uses absolute imports `from src...` and the hard-coded path `"src/data.txt"`, so it only works as `python -m src.main` with CWD = `Project sdaia/`. Runtime dependencies inferred from imports: `requests`, `numpy`, `python-dotenv`.

---

## 2. Current flows

### 2.1 Ingestion
`main.run(file_path)` → `open(..., encoding="utf-8").read()` → `RAGPipeline.build_index(text)`. TXT only; no upload, no validation, single hard-coded file. [`main.py:14-20`](../../Project%20sdaia/src/main.py)

### 2.2 Chunking
`chunk_text(text, chunk_size=500, overlap=50)` slices raw characters. No awareness of words, sentences, paragraphs, headings, pages or language. [`rag/chunker.py:1-10`](../../Project%20sdaia/src/rag/chunker.py)

### 2.3 Embeddings
`POST https://openrouter.ai/api/v1/embeddings`, model **`openai/text-embedding-3-small`** (hard-coded), **one HTTP request per chunk**, no timeout, no status check, no retry. [`rag/embeddings.py:9-22`](../../Project%20sdaia/src/rag/embeddings.py)

### 2.4 Vector store / retrieval
Python lists of vectors + texts; brute-force cosine over all vectors in a loop; `top_k=5`; returns **text only** (no IDs, no scores, no metadata). Prints every similarity score and an 80-char excerpt of each top chunk to stdout. [`rag/vector_store.py:17-37`](../../Project%20sdaia/src/rag/vector_store.py)

### 2.5 Generation
`OpenRouterLLM.invoke(prompt)` → `POST /api/v1/chat/completions`, model **`openai/gpt-4o-mini`** (hard-coded), single user message, no temperature/max_tokens, no timeout. Any exception is converted to the **string** `"ERROR: ..."` and returned as if it were model output. [`llm/openrouter.py:13-33`](../../Project%20sdaia/src/llm/openrouter.py)

### 2.6 Summarizer agent
`main.py` retrieves the 5 chunks most similar to **the first 200 characters of the document** and passes them to `BaseAgent(SUMMARIZER_PROMPT)`. [`main.py:22-36`](../../Project%20sdaia/src/main.py)

### 2.7 Question generator agent
Receives **the summary**, not the document. [`main.py:50-54`](../../Project%20sdaia/src/main.py)

### 2.8 Chatbot
`ChatBot()` creates its **own** `RAGPipeline` and `OpenRouterLLM`, re-reads and re-embeds the file, then answers single-turn questions with a "context only" prompt asking for `(Chunk X)` citations. [`chatbot/chat.py`](../../Project%20sdaia/src/chatbot/chat.py)

### 2.9 ReAct engine (`BaseAgent`)
Loop up to `max_steps=10`: prompt = system prompt + `INPUT: {observation}`; stop if response starts with `FINAL`; if it contains `ACTION:` parse `ACTION:` / `INPUT:` lines, run tool, replace observation with the tool result. Loop detection via MD5 of responses and observations. [`agent/base.py`](../../Project%20sdaia/src/agent/base.py)

### 2.10 Tool registry
`TOOLS = {"read_file": read_file}`; `read_file` opens any path the LLM supplies. [`tools/`](../../Project%20sdaia/src/tools/)

### 2.11 Observability
`@observe` decorator prints function duration — **never applied anywhere** (grep: zero usages). Actual "observability" is `print()` in `BaseAgent` (`verbose=True`) and `VectorStore`. `tool_logs` are collected and returned but never displayed by `main.py`.

---

## 3. Model audit (verified from code)

| Purpose | Model ID in code | Location | Status in OpenRouter catalog (fetched 2026-11-16) |
|---|---|---|---|
| Text generation (chatbot + both agents) | `openai/gpt-4o-mini` | `llm/openrouter.py:20` | Available, ctx 128k, $0.15/M in, $0.60/M out |
| Embeddings | `openai/text-embedding-3-small` | `rag/embeddings.py:17` | Available, ctx 8192, $0.02/M |
| Document processing / OCR / vision | **none** | — | — |
| Reranking | **none** | — | — |

Both IDs are hard-coded string literals; neither is configurable.

---

## 4. Confirmed defects

Severity: **H** = produces wrong/ungrounded output or a security exposure; **M** = cost, reliability or correctness degradation; **L** = hygiene.

| # | Sev | Defect | Evidence |
|---|---|---|---|
| D1 | **H** | **Citations are structurally impossible to get right.** The prompt asks for `(Chunk X)` but the context is `"\n\n".join(chunks)` with no labels, so the model cannot know any chunk number. Any citation it prints is invented. | `chatbot/chat.py:19-49` |
| D2 | **H** | **Summary does not cover the document.** It summarizes only the 5 chunks (≈2,500 chars) most similar to the first 200 characters. For any document longer than ~2.5k chars, most content is ignored. | `main.py:22-23` |
| D3 | **H** | **Generated questions are derived from the summary**, so they inherit D2's coverage loss and any summary hallucination; they are not tied to document evidence. | `main.py:50-54` |
| D4 | **H** | **Arbitrary file read via the agent tool.** `read_file` accepts any LLM-chosen path; the `src/` prefix is not a sandbox (`src/../.env` resolves outside it). Because document text is placed in the prompt, a document containing "ACTION: read_file / INPUT: ../.env" could exfiltrate secrets into the output (prompt injection → tool abuse). | `tools/file_tool.py:1-6`, `agent/base.py:70-76` |
| D5 | **H** | **API errors become answers.** `invoke()` returns `"ERROR: <exception>"` as normal content; the chatbot prints it as an answer and the agent treats it as a model step. Exception text can include the request URL and HTTP details. | `llm/openrouter.py:32-33` |
| D6 | M | **The ReAct loop has no memory.** Each step's prompt contains only the latest observation; after a tool call the original task input is replaced by `TOOL RESULT`, so the model loses the task. There is no scratchpad of prior thoughts/actions. | `agent/base.py:29-34, 101` |
| D7 | M | **Agent state leaks across runs.** `seen_responses` / `seen_observations` are instance attributes never reset in `run()`. Reusing an agent instance causes false "repeated response" stops. Latent today because `main.py` creates new instances. | `agent/base.py:13-14` |
| D8 | M | **Responses that are neither FINAL nor ACTION re-send the identical prompt**, wasting a call and usually ending in "repeated response detected". `FINAL` detection is case-sensitive and requires it to be the first token. | `agent/base.py:57, 66, 105` |
| D9 | M | **Duplicate indexing.** The same file is embedded twice (once in `main.run`, once in `ChatBot.load_file`) → double embedding cost and two divergent indexes. | `main.py:19-20`, `chatbot/chat.py:8,14` |
| D10 | M | **No HTTP timeouts, retries, or status checks for embeddings**; an error response raises an opaque `KeyError: 'data'`. One request per chunk (no batching) → N round-trips per document. | `rag/embeddings.py:10-22` |
| D11 | M | **No timeouts on chat completions** → a stalled connection hangs the CLI indefinitely. | `llm/openrouter.py:27` |
| D12 | M | **No source metadata anywhere.** Retrieval returns bare strings; there is no document ID, filename, page, or offset. Multi-document use and real citations are impossible without new data contracts. | `rag/vector_store.py:37` |
| D13 | M | **Character chunking splits words and sentences** (including Arabic words, which breaks embedding quality and quoted evidence). With `len(text)` an exact multiple of 450 + 50, a trailing 50-char overlap-only chunk is created. `overlap >= chunk_size` would loop forever (no guard). | `rag/chunker.py:5-8` |
| D14 | M | **Document content is printed to stdout** (top-chunk excerpts, full agent responses). In a server context this would leak document contents into logs. | `rag/vector_store.py:25-35`, `agent/base.py:40-41` |
| D15 | M | **Chatbot is single-turn**: no conversation history, so follow-up questions ("and what about the second one?") cannot be resolved. | `chatbot/chat.py:17-55` |
| D16 | L | Cosine similarity divides by zero for a zero vector (NaN scores). | `rag/vector_store.py:15` |
| D17 | L | `OpenRouterEmbeddings` does not check for a missing API key (fails later with HTTP 401 → `KeyError`). | `rag/embeddings.py:6` |
| D18 | L | `@observe` is dead code; README overstates observability ("tracks agent execution steps, tool calls..."). | `observability/observe.py` |
| D19 | L | Summarizer prompt advertises `read_file` though the content is already provided; this invites unnecessary (and, per D4, unsafe) tool calls. | `agent/prompts.py:4-11` |
| D20 | L | No dependency manifest, no `.gitignore`, committed `.pyc` files, CWD-dependent paths, no tests. | repo root |

## 5. Risks (not yet observed, depend on scale/inputs)

| # | Risk | Why |
|---|---|---|
| R1 | Context overflow / silent truncation for long documents if code is changed to pass whole documents | No token counting anywhere |
| R2 | Brute-force O(N) Python-loop search becomes slow above ~50k chunks | Per-vector `np.array` conversion in a loop; acceptable for session-scale data if vectorized |
| R3 | Rate limiting (HTTP 429) during indexing of large documents | One request per chunk, no backoff |
| R4 | Arabic quality of `text-embedding-3-small` is unmeasured | No Arabic retrieval evaluation exists |
| R5 | Cross-session/document contamination once multiple documents exist | Single global store with no filters |

---

## 6. What must be preserved

- The **custom ReAct engine** concept (`BaseAgent`: step loop, tool dispatch, loop detection, step timing, `tool_logs`) — refactor, do not replace with a framework.
- The **Tool Registry** pattern (name → callable).
- **Summarizer** and **Question Generator** agents and their prompts' intent.
- **ChatBot** "answer only from context / say I don't know" contract.
- **OpenRouter** as the inference provider; `requests`-based client is acceptable (no SDK lock-in needed).
- A **CLI workflow** (`python -m src.main <file>`) for development.

## 7. What does NOT need rewriting

- The in-memory NumPy vector store is a reasonable fit for **temporary, session-scoped** indexes (thousands to tens of thousands of chunks). It needs metadata, filtering, deletion and vectorization — not a vector database.
- `requests` is sufficient; an async rewrite is not required for a backend that runs ingestion in a worker pool.

## 8. Audit limitations

- Static review only; no runtime verification of API behavior was possible.
- The quality claims in `README.md` were not tested.
