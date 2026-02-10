# 08 - Current Challenges & Limitations

**Last Updated:** February 9, 2026  
**Status:** Active Issues List

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Challenges](#technical-challenges)
3. [Data Quality Issues](#data-quality-issues)
4. [User Experience Limitations](#user-experience-limitations)
5. [Hardware & Resource Constraints](#hardware--resource-constraints)
6. [Test Environment Specifications](#test-environment-specifications)

---

## Executive Summary

While TigerBrain v2.0 "TigerStack" enables powerful local-first research assistance, we currently face significant challenges in **inference latency**, **PDF parsing fidelity**, and **graph scalability**. This document details these hurdles to inform future development (Phase 4-5).

---

## Technical Challenges

### 1. LLM Inference Latency (Local)
*   **Problem:** Generating a full response takes 15-45 seconds on standard hardware.
*   **Cause:** Running unquantized 7B models (Qwen 2.5) locally on CPU/Metal.
*   **Impact:** User frustration; "thinking" spinner runs too long.
*   **Mitigation Strategy:** 
    *   Switch to 4-bit quantized models (`q4_0`)
    *   Implement streaming responses (partially done)
    *   Use smaller specialized models for entity extraction (Phase 3)

### 2. Context Window Fragments
*   **Problem:** Retrieving too many documents (e.g., 20 papers) overflows the 8k token limit.
*   **Cause:** Raw text from PDFs is dense; 5 papers can exceed 8k tokens.
*   **Impact:** "Context length exceeded" errors or truncation of critical info.
*   **Current Fix:** Strict limit of top-5 results.
*   **Long-term Fix:** Semantic summarization layer before Context injection.

### 3. Graph Traversal Complexity
*   **Problem:** Multi-hop queries (e.g., "Find faculty connecting CV and NLP") explode combinatorially.
*   **Cause:** NetworkX is in-memory and single-threaded; traversing >2 hops is O(k^n).
*   **Impact:** Complex "Exploratory" queries are slow (>5s).
*   **Planned Fix:** Migrate to Neo4j or KuzuDB for optimized graph algorithms.

---

## Data Quality Issues

### 1. PDF Distillation Brittleness
*   **Problem:** `DeepDistiller` fails on older two-column PDFs or those with complex layouts.
*   **Symptoms:** merged text across columns, garbled tables, missing references.
*   **Impact:** "Research Cards" sometimes contain gibberish or miss key findings.
*   **Status:** High Priority. Evaluating `marker` and `Nougat` OCR tools to replace `PyMuPDF`.

### 2. Entity Resolution Ambiguity
*   **Problem:** "Flash Memory" and "NAND Flash" are treated as separate concept nodes.
*   **Impact:** Graph fragmentation; queries for one term miss papers using the synonym.
*   **Status:** `EntityResolver` uses simple fuzzy matching. Need semantic embedding-based merging (Phase 5).

### 3. Crawler Traps
*   **Problem:** RIT directory sometimes serves "Access Denied" or infinite redirect loops.
*   **Impact:** Missing faculty profiles in `rit_data_v2.json`.
*   **Current Fix:** Manual delays and user-agent rotation.

---

## User Experience Limitations

### 1. No Conversational Memory
*   **Problem:** Asking "Tell me more about him" fails if the previous context isn't explicitly re-sent.
*   **Cause:** State management is basic; previous entities aren't carried forward to the Retriever.
*   **Impact:** Interaction feels robotic; users must repeat names.

### 2. Citation Hallucination Risk
*   **Problem:** LLM sometimes attributes a real paper to the wrong author in the summary text.
*   **Cause:** "Lost in the middle" phenomenon in long context windows.
*   **Status:** Hard prompt engineering constraints added, but 5-10% error rate persists.

---

## Hardware & Resource Constraints

The system performance is heavily dependent on the host machine. 

### Recommended vs. Minimum Specs

| Component | Minimum (Functioning) | Recommended (Smooth) |
|-----------|------------------------|----------------------|
| **RAM** | 16GB (Swap heavy) | 32GB+ (Full in-memory) |
| **GPU** | Integrated (Slow) | NVIDIA RTX 3060 / Mac M1 Pro |
| **Storage** | 20GB SSD | 100GB NVMe (Fast graph load) |

### Current Resource Usage
*   **Idle:** 2.4GB RAM (Chroma + Graph)
*   **Active Inference:** 12GB - 16GB RAM (Model loaded)
*   **Graph Load Time:** ~4.2 seconds (Cold start)

---

## Test Environment Specifications

*User Specific Configuration*

*   **Machine:** [USER TO FILL: e.g., MacBook Pro M3 Max]
*   **OS:** macOS [Version]
*   **Model Used:** `tigerbuddy` (Qwen 2.5 7B)
*   **Quantization:** [e.g., q4_0 / fp16]

> **Note:** Your specific PC specifications are **not** currently auto-detected or stored in the documentation. You can update this section with your exact build details for reference.
