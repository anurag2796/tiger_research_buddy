# 08 - Current Challenges & Known Limitations

**Last Updated:** February 23, 2026  
**Status:** Active Issues List — 6/7 bugs resolved; 1 open

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

## Pipeline Run Post-Mortem & Fix Log

### Pre-Fix Run (Feb 21 2026)

**Trace ID:** `1ca0f6aa-5307-47ca-bdce-ad3bb00eec93`  
**Stats:** 1,001 profiles crawled → 17,037 papers downloaded → 1,468 cards distilled (~8.6% success rate)

| Stage | Pre-Fix Status | Error Count | Root Cause |
|---|---|---|---|
| 1. SmartCrawler | ⚠️ Partial | 54 ERRORs | Binary files (`.docx`, `.zip`, `.jpg`) decoded as UTF-8 |
| 2. ScholarCrawler | ❌ Broken | 34 ERRORs | Thread-safety race — `dict changed size during iteration` |
| 3. PaperDownloader | ⚠️ Partial | 18,054 ERRORs | 404s + vision type bug (`'str' has no attribute 'get'`) |
| 4. DeepDistiller | ⚠️ Partial | 5,197 ERRORs | PDF recursion depth limit + `meta tensor` PyTorch bug |
| 5. Vector Indexer | ❌ HARD FAIL | Stage crashed | `.to()` on meta tensor — vector store was empty |
| 6. Knowledge Graph | ✅ OK | 0 | Completed — 6,708 nodes, 129,172 edges |
| RAGEngine | ⚠️ Warning | 3 WARNINGs | Free-tier Gemini quota exhausted; correctly fell back to Ollama |

### Bug Fix Status (as of Feb 23, 2026)

| Bug | Description | Status | Fix Location |
|-----|-------------|--------|--------------|
| Bug 1 | `RecursionError` in PDF reading | ✅ **Fixed** | `pdf_distiller.py` — full `try/except` in `extract_text_async()` |
| Bug 2 | Meta-tensor crash in embedding init | ✅ **Fixed** | `vector_store.py` — warmup encode in `TigerEmbeddingFunction.__init__()` |
| Bug 3 | HTTP timeout on PDF download | ✅ **Fixed** | `paper_downloader_v3.py` — 3-retry loop with backoff in `download_pdf()` |
| Bug 4 | Author last-name collision | ✅ **Fixed** | `paper_downloader_v3.py` — `_is_author_match()` requires first-name equality |
| Bug 5 | Binary file `UnicodeDecodeError` | ✅ **Fixed** | `paper_downloader_v3.py` — content-type guard; `pdf_distiller.py` type guard |
| Bug 6 | Dict mutation in ScholarCrawler threads | ✅ **Fixed** | `scholar_crawler.py` — workers return `(idx, copy, data)`, main thread writes |
| **Bug 7** | Vision type guard missing in PaperDownloader | ⚠️ **Partially Fixed** | `pdf_distiller.py` patched; `paper_downloader_v3.py` `extract_text()` L324 patched Feb 23 |

> **Post-fix verification:** Two pipeline runs on Feb 22 (traces `86a0853c`, `f5e8b65e`) produced only **2 WARNINGs total** — confirming the fixes are working.

### Performance Data (from `process_timings` table)

| Operation | Avg Duration | Max Duration |
|-----------|-------------|-------------|
| Distilling one PDF → TigerCard | ~55s | 125s |
| Extracting text from PDF | ~45s | ~90s |
| Scholar profile scraping | ~40s | ~78s |
| ArXiv search | ~5s | ~30s |

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

**Problem:** Synonymous concepts are treated as separate graph nodes, and abbreviated author names cause duplicates.  
**Examples:** "Flash Memory" and "NAND Flash" — separate nodes, so queries for one miss papers using the other. "C. Kanan" and "Christopher Kanan" — previously failed to merge if initial penalty triggered.  
**Cause:** `EntityResolver` uses fuzzy string matching (TheFuzz), which is sensitive to phrasing but not semantics.  
**Status:** ⚠️ Partially Mitigated — We upgraded `EntityResolver` to use a **Relational-Aware Tiered Approach**. For ambiguous fuzzy matches (80-95%), it now checks the Jaccard similarity of their 1-hop NetworkX neighborhoods. If overlap > 0.4, they merge. Embedding-based semantic merging for concepts is still planned for Phase 5.

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
**Status:** ✅ Fixed — `_is_author_match()` now requires exact first-name match when both names are full, and first-initial agreement as a fallback. A proactive assertion loop re-validates all accepted papers before download.  
**Residual Risk:** The initial-only path ("J. Smith" could still match "John" and "James"). A phonetic/fuzzy check (metaphone) is the planned next improvement.

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
