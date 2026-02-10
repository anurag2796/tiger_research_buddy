# Analysis of Gemini's "TigerStack" Proposal

**Source:** `docs/challenges/gemini_solution.md`
**Date:** February 9, 2026
**Status:** Under Review for Phase 4/5 Implementation

---

## Executive Summary
Gemini has proposed a sophisticated, "2026-standard" architecture dubbed **TigerStack**. It addresses our core bottlenecks by shifting from heuristic parsing to computer vision, and from in-memory graphs to disk-based embedded databases.

## Key Recommendations & Feasibility Analysis

### 1. Ingestion: The "Vision-First" Revolution
*   **Gemini Proposal:** Abandon `PyMuPDF` (heuristic) for **MinerU 2.5** (aka Magic-PDF) and **MiniCPM-V 4.5**.
*   **Why:** Traditional parsers fail on 2-column layouts and tables. VLMs "see" the document structure.
*   **Feasibility:** 
    *   **High (on Mac M-series).** MinerU is designed for high-fidelity extraction.
    *   **Hardware Requirement:** Need to verify if MiniCPM-V 8B runs smoothly alongside our Qwen 2.5 7B model.
*   **Action Item:** Create a POC `src/crawlers/vision_crawler.py` using MinerU.

### 2. Graph Database: Bighorn (Post-Kùzu Fork)
*   **Gemini Proposal:** Migrate from `NetworkX` (RAM-bound) to **Bighorn** (embedded, disk-based, CSR indices).
*   **Why:** NetworkX is slow for 2+ hop queries on large graphs. Bighorn is optimized for local bare-metal speed (like DuckDB for graphs).
*   **Feasibility:** 
    *   **Medium/Unknown.** Bighorn is a newer fork of KuzuDB. We need to verify its Python client maturity and stability.
    *   **Alternative:** **KuzuDB** itself is still very active (despite the "archived" claim in the prompt, we should double-check its status). `DuckDB` + SQL macros is another strong contender.
*   **Action Item:** Benchmark `NetworkX` vs `KuzuDB` vs `Bighorn` for 2-hop traversal time.

### 3. Context: LazyGraphRAG & Chain of Density
*   **Gemini Proposal:** 
    *   **LazyGraphRAG:** Don't pre-summarize everything (too expensive locally). Summarize "communities" on-the-fly during query time.
    *   **Chain of Density (CoD):** A recursive prompting technique to pack more entities into the context window.
*   **Feasibility:** **High.** These are logic/prompt changes, not infrastructure overhauls.
*   **Action Item:** Implement `src/generation/chain_of_density.py` immediately to improve response quality.

### 4. Memory: Letta (Agent OS)
*   **Gemini Proposal:** Use **Letta** (formerly MemGPT) to manage "Core Memory" (User/Persona) and "Archival Memory" (History).
*   **Why:** Enbles "Stateful" agents that remember user preferences across sessions.
*   **Feasibility:** 
    *   **Medium.** Letta is powerful but adds complexity (requires a separate server process/Docker).
    *   **Lite Version:** We might implement a lightweight SQLite-based memory module first before full Agent OS adoption.
*   **Action Item:** Prototype a simple `sqlite` session store for Streamlit first.

---

## Proposed Implementation Roadmap

1.  **Immediate Win (Week 6):** Implement **Chain of Density (CoD)** prompting for better answers.
2.  **Short Term (Week 7):** Replace `PyMuPDF` with **MinerU/Marker** for vastly better PDF reading.
3.  **Medium Term (Week 8):** Benchmark **KuzuDB/Bighorn** to prepare for Graph scale-up.
4.  **Long Term (Phase 5):** Integrate **Letta** for full agentic memory.

---

## Conclusion
The "TigerStack" vision is compelling and aligns perfectly with our "Local-First" philosophy. It moves us from a "Student Project" architecture to an "Enterprise RAG" architecture while keeping data private.
