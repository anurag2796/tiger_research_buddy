# 08 - Current Challenges & Known Limitations

**Last Updated:** February 22, 2026  
**Status:** Active Issues List

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Pipeline Run Post-Mortem (Feb 21 2026)](#pipeline-run-post-mortem-feb-21-2026)
3. [Technical Challenges](#technical-challenges)
4. [Data Quality Issues](#data-quality-issues)
5. [User Experience Limitations](#user-experience-limitations)
6. [Hardware & Resource Constraints](#hardware--resource-constraints)
7. [Test Environment Specifications](#test-environment-specifications)

---

## Executive Summary

TigerBrain v2.2 delivers fast local-first research assistance through its Hybrid RAG architecture, 6-stage pipeline, and the apple_fast PDF engine. However, three primary challenge areas remain: **LLM inference latency**, **entity resolution accuracy at scale**, and **the absence of conversational memory**. This document details these limitations and their current mitigations.

---

## Pipeline Run Post-Mortem (Feb 21 2026)

**Trace ID:** `1ca0f6aa-5307-47ca-bdce-ad3bb00eec93`  
**Stats:** 1,001 profiles crawled → 17,037 papers downloaded → 1,468 cards distilled (~8.6% success rate)

### Summary Table

| Stage | Status | Error Count | Root Cause |
|---|---|---|---|
| 1. SmartCrawler | ⚠️ Partial | 54 ERRORs | Binary files (`.docx`, `.zip`, `.jpg`) decoded as UTF-8 |
| 2. ScholarCrawler | ❌ Broken | 34 ERRORs | Thread-safety race — `dict changed size during iteration` |
| 3. PaperDownloader | ⚠️ Partial | 18,054 ERRORs | 404s + vision bug (`'str' has no attribute 'get_image'`) |
| 4. DeepDistiller | ⚠️ Partial | 5,197 ERRORs | PDF recursion depth limit + `meta tensor` PyTorch bug |
| 5. Vector Indexer | ❌ HARD FAIL | Stage crashed | `torch.nn.Module.to()` on meta tensor — vector store is **empty** |
| 6. Knowledge Graph | ✅ OK | 0 | Completed successfully — 6,708 nodes, 129,172 edges |
| RAGEngine | ⚠️ Warning | 3 WARNINGs | Free-tier Gemini quota exhausted; fell back to Ollama |

### Failure Details

#### ❌ Stage 5 — Vector Indexer Hard Crash (P0)
The embedding model was initialized as a PyTorch **meta tensor** (shape-only, no weights) then moved with `.to(device)` — an illegal operation. Stage crashed in ~2 seconds. **The vector store is empty; RAG retrieval is non-functional.**
> **Fix:** Replace `.to(device)` with `.to_empty(device)` followed by proper weight loading (`load_state_dict`).

#### ❌ Stage 2 — ScholarCrawler Race Condition (P0)
A shared Python `dict` is mutated by one thread while another iterates it — `RuntimeError: dictionary changed size during iteration`. All 34 affected faculty threads crashed. Scholar enrichment returned **0 enriched** this run.
> **Fix:** Wrap shared dict mutations in a `threading.Lock()`.

#### ⚠️ Stage 4 — DeepDistiller (Two Bugs) (P1)
- **`RecursionError: maximum recursion depth exceeded`** — PDF parser hits Python's default recursion cap on deeply nested/malformed PDF object trees. Thousands of files silently skipped.
  > **Fix:** Call `sys.setrecursionlimit(5000)` before extraction, or switch to `pymupdf`/`pdfplumber` (non-recursive parsers).
- **`'str' object has no attribute 'get_image'`** — vision extraction is passed a raw file path string instead of a `Page` object. All multimodal annotations are silently broken.
  > **Fix:** Identify the call site passing a `str` to the image extractor and correct the type.

#### ⚠️ Stage 3 — PaperDownloader (P2)
Mass 404 errors on ArXiv URLs (`arxiv.org/pdf/<id>v<N>`) — versioned PDFs that no longer exist. Vision extraction also failing (same `'str' has no 'get_image'` bug as Stage 4).
> **Fix:** Add fallback URL strategy (try `v1` if `vN` returns 404); fix vision type bug.

#### ⚠️ Stage 1 — SmartCrawler Binary Files (P3)
Crawler attempts to decode binary responses (`.docx`, `.zip`, `.jpeg`, `.pptx`) as UTF-8 text. These are admin/template files — low impact on faculty data, but adds noise.
> **Fix:** Check `Content-Type` response header; skip non-`text/html` responses.

#### ⚠️ RAGEngine — Gemini Quota (P4)
Free-tier `gemini-2.0-flash` quota exhausted on 3 occasions during the RAG verification run. System correctly fell back to Ollama — non-fatal.
> **Fix:** Upgrade to a paid API key or add smarter per-minute backoff.

---

## Technical Challenges

### 1. LLM Inference Latency

**Problem:** Full-precision models (Qwen 2.5 7B) take 15–45 seconds per response on CPU-only hardware.  
**Cause:** Unquantized models require full float16 precision; large context windows (8k) compound this.  
**Impact:** "Thinking" spinner runs too long; poor user experience on underpowered hardware.

**Current Mitigations:**
- Use `qwen2.5:7b-q4_0` (4-bit quantized) — 2–3× faster for ~10% quality tradeoff.
- Streaming responses implemented (partial text appears progressively).
- `@st.cache_resource` loads the model once per Streamlit session.

**Planned Fix:** Smaller "router model" for intent classification; full model only for synthesis.

---

### 2. Context Window Ceiling

**Problem:** Retrieving too many documents overflows the 8k token limit.  
**Cause:** Dense academic text — 5 full papers can exceed 8k tokens.  
**Impact:** "Context length exceeded" errors or silent truncation of critical information.

**Current Fix:** Hard limit of top-5 retrieval results sent to LLM context.  
**Long-term Fix:** Semantic summarization layer — compress each retrieved document before injection.

---

### 3. Graph Traversal Complexity

**Problem:** Multi-hop queries ("Find faculty connecting CV and NLP") explode combinatorially.  
**Cause:** NetworkX is in-memory and single-threaded; >2-hop traversal is O(k^n).  
**Impact:** Complex "Exploratory" queries are slow (>5s) or timeout.

**Planned Fix:** Migrate to Memgraph or Neo4j at the 5k-paper threshold (p95 > 200ms triggers migration). See `docs/project_journey.md` §10 for the full graph DB migration plan.

---

### 4. Entity Resolution Ambiguity

**Problem:** Synonymous concepts are treated as separate graph nodes.  
**Examples:** "Flash Memory" and "NAND Flash" — separate nodes, so queries for one miss papers using the other.  
**Cause:** `EntityResolver` uses fuzzy string matching (TheFuzz), which is sensitive to phrasing but not semantics.  
**Status:** Threshold raised to 90% similarity. Embedding-based semantic merging is planned for Phase 5.

---

### 5. Missing Cross-Encoder Re-Ranking

**Problem:** RRF fusion (Vector + BM25) ranks by signal agreement but doesn't score query-document relevance precisely.  
**Impact:** Highly relevant documents may appear at rank 4–5 while a superficially similar document appears at rank 1.  
**Planned Fix:** Cross-encoder re-ranking step (e.g., `bge-reranker-v2-m3`) on top-20 RRF results before sending to LLM.

---

## Data Quality Issues

### 1. PDF Distillation Edge Cases

**Problem:** `DeepDistiller` fails on deeply nested PDF object trees (recursion), malformed page objects for vision extraction, and certain PDFs that trigger the PyTorch meta-tensor bug.  
**Symptoms:** `RecursionError`, `'str' object has no attribute 'get_image'`, `Cannot copy out of meta tensor`. Only 1,468 / 17,037 papers successfully distilled in the Feb 21 2026 run (~8.6%).  
**Status:** ❌ Active — three separate bugs identified in the Feb 21 run (see Post-Mortem above).  
**Remaining risk:** Very old scanned documents (pre-1990) — consider `--engine marker` for those.

### 2. Crawler Coverage Gaps

**Problem:** RIT directory occasionally serves "Access Denied" pages or infinite redirect loops.  
**Impact:** Missing faculty profiles in `rit_data.json`.  
**Current Fix:** Manual delays (`CRAWL_DELAY`) + user-agent rotation.  
**Monitoring:** Check `data/publications/download_summary.json` after each run for "skipped" entries.

### 3. Author Name Collision

**Problem:** Last-name-only matches can link a paper to the wrong faculty member.  
**Status:** Fixed — `_is_author_match()` now rejects last-name-only collisions. Author match requires at minimum first initial agreement.

### 4. Stale Data

**Problem:** Faculty profiles and paper counts become stale between pipeline runs.  
**Planned Fix:** KnowledgeDaemon's Watcher loop (Phase 5) will automatically detect new PDFs and trigger incremental updates.

---

## User Experience Limitations

### 1. No Conversational Memory

**Problem:** Each chat query is independent. Asking "Tell me more about him" fails — the previous entity is not in context.  
**Cause:** State management sends only the current query to the Retriever; session history is not factored into retrieval.  
**Impact:** Interaction feels robotic; users must repeat names explicitly.  
**Planned Fix:** Entity carry-forward — extract mentioned entities from the last N turns and inject as filters into the next retrieval.

### 2. Citation Hallucination Risk

**Problem:** LLM sometimes attributes a real paper to the wrong author in the synthesized response text.  
**Cause:** "Lost in the middle" phenomenon — the LLM loses track of source attribution when context exceeds ~6k tokens.  
**Status:** Hard prompt constraints added ("CITE SOURCES from context only"). Residual error rate: ~5–10%.  
**Planned Fix:** Citation grounding layer — post-process LLM output to verify each citation against retrieved sources.

---

## Hardware & Resource Constraints

### Recommended vs. Minimum Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 16GB | 32GB+ |
| **GPU** | Integrated (will be slow) | Apple M1 Pro / M2 / M3, or NVIDIA RTX 3060+ |
| **Storage** | 20GB SSD | 100GB NVMe |
| **CPU** | 4 cores | 8+ cores or Apple Silicon |

### Current Resource Usage (v2.2, M-Series Mac)

| State | RAM | Notes |
|-------|-----|-------|
| Idle (graph + chroma loaded) | ~2.4GB | Streamlit not open |
| Active inference (q4_0 model) | ~6–8GB | Quantized Qwen 2.5 |
| Active inference (fp16 model) | ~12–16GB | Full-precision Qwen 2.5 |
| PDF distillation (apple_fast) | +2GB | Surya + GMFT models loaded |

### Graph Cold Start Time

| Graph Size | Load Time |
|------------|-----------|
| ~45k nodes (current) | ~2.0s |
| ~100k nodes (estimated) | ~4–5s |

---

## Test Environment Specifications

> **Note:** Update this section with your hardware for accurate performance reference.

- **Machine:** Apple Silicon Mac (M-series) — user-specific model
- **OS:** macOS (current version)
- **Python:** 3.10+
- **Ollama Model:** `tigerbuddy` (Qwen 2.5 7B)
- **Quantization:** `q4_0` recommended; `fp16` for highest accuracy
- **PDF Engine:** `apple_fast` (default) with MPS acceleration

---

**Related Reading:**
- `docs/project_journey.md` §14 — full bug and challenge history with fixes applied
- `docs/wiki/07_troubleshooting.md` — step-by-step fixes for known errors
