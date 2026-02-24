# TigerResearchBuddy: The Project Journey

**Last Updated:** February 20, 2026  
**Covers:** Project inception → v2.2 (Fast-by-Default), evaluation framework, external architecture reviews

---

## Table of Contents

1. [The Spark — Why We Built This](#1-the-spark--why-we-built-this)
2. [v0.1 — The First Prototype](#2-v01--the-first-prototype)
3. [v1.0 — MVP: Basic RAG Goes Live](#3-v10--mvp-basic-rag-goes-live)
4. [The Overnight Build — Five Phases in One Night](#4-the-overnight-build--five-phases-in-one-night)
5. [Architecture Decision: V2 "TigerStack"](#5-architecture-decision-v2-tigerstack)
6. [Migration Rationale: Why We Changed Everything](#6-migration-rationale-why-we-changed-everything)
7. [Experiment 4 — The TigerBrain Knowledge Graph](#7-experiment-4--the-tigerbrain-knowledge-graph)
8. [v2.1 — Vision-First Ingestion](#8-v21--vision-first-ingestion)
9. [v2.2 — Fast-by-Default: Apple Silicon Optimization](#9-v22--fast-by-default-apple-silicon-optimization)
10. [AI Architecture Reviews & The Final Implementation Plan](#10-ai-architecture-reviews--the-final-implementation-plan)
11. [Entity Extraction Deep Dive](#11-entity-extraction-deep-dive)
12. [Hybrid Retrieval: From Concept to Code](#12-hybrid-retrieval-from-concept-to-code)
13. [Code Quality & Engineering Improvements](#13-code-quality--engineering-improvements)
14. [Challenges, Bugs & How We Fixed Them](#14-challenges-bugs--how-we-fixed-them)
15. [Brainstorming & Ideas Captured Along the Way](#15-brainstorming--ideas-captured-along-the-way)
16. [Future Roadmap](#16-future-roadmap)

---

## 1. The Spark — Why We Built This

### The Elevator Pitch
> *"Finding a research mentor at RIT shouldn't be harder than doing the actual research."*

**The Problem:**  
Students at RIT's Golisano College of Computing face a "Paradox of Choice":
- **Too Much Data:** 100+ faculty, 1,000+ papers, dozens of lab websites.
- **Siloed Information:** Department sites are disconnected from Google Scholar profiles.
- **Keyword Failure:** Searching "AI" returns 50 professors. Searching "Neuro-symbolic AI" returns zero—even if three professors work on it—because they use different terminology.

**The Vision:**  
An AI-powered **Digital Advisor** (not just a search engine) that synthesizes advice like a knowledgeable friend would. Instead of "Here are five links about NLP," TigerResearchBuddy says: *"If you're interested in NLP, you should speak to Prof. Huenerfauth (Accessibility) or Prof. Kanan (Vision-Language). Here is how their work differs…"*

**Technical Pitch:**  
Built a specialized **RAG (Retrieval-Augmented Generation)** system grounded in actual RIT faculty data. Students can ask *"Who works on computer vision?"* or *"What is Dr. Kanan's email?"* and get instant, fact-checked answers.

**Key Design Principles Established at the Start:**
- Privacy-first: all AI runs locally via Ollama. No data leaves the machine.
- Zero per-query cost after initial setup.
- Grounded: refuses to guess if the vector distance is too high.

---

## 2. v0.1 — The First Prototype

The very first implementation was a simple Python script:
- **Scraper:** `BeautifulSoup` + Regex + hardcoded CSS selectors targeting Golisano College.
- **Storage:** Plain JSON files.
- **Intelligence:** Similarity search via Gemini Cloud API. No graph. No local model.
- **Problem:** Brittle CSS selectors broke every time RIT updated their site. Prof. Kinsman's profile was an early casualty.

**Lesson learned:** Structural selectors are maintenance nightmares. Semantic understanding is necessary.

---

## 3. v1.0 — MVP: Basic RAG Goes Live

The prototype graduated to a proper MVP:
- **Vector Store:** ChromaDB (file-based, Python-native, zero config).
- **Embedding Model:** `all-MiniLM-L6-v2` (384 dimensions, 512 context window).
- **Intelligence:** Basic RAG pipeline — embed faculty bios → semantic search → LLM answer.
- **UI:** Streamlit interface with chat input.
- **Safety:** Custom `Intent Classifier` (Faculty Lookup vs. Topic Search vs. Off-topic), Dynamic Confidence Thresholds to prevent hallucinations, Regex-based Response Post-Processor.
- **Demo Script:** Ask *"What is the weather?"* → Bot refuses politely. Ask *"Who works on Machine Learning?"* → Bot lists verified faculty.

**Limitations exposed:**
- No graph: couldn't answer "Who collaborates with Prof X?" 
- Hallucinated author attributions in long contexts.
- ChromaDB filtering was slow on metadata queries.
- MiniLM truncated long research paper summaries at 512 tokens.

---

## 4. The Overnight Build — Five Phases in One Night

An autonomous overnight session implemented five major feature phases in a single run. All phases were tested and passed.

### Phase 1: Agent Intelligence & Persona
- Created "Encouraging Tiger" persona (`data/prompts/role.md`).
- Created `data/prompts/skills.md` for tool-use instructions.
- Built custom Ollama `Modelfile` (`tigerbuddy`) baked with the system prompt.
- Integrated persona into `web_app.py` and `ollama_client.py`.

### Phase 2: Multi-Department Integration
- Extended the crawler from "Computing only" to Engineering, Science, and Liberal Arts colleges.
- Implemented recursive directory link-following (`_crawl_area_details` now looks for "People"/"Directory" sub-links).
- Config updated with `COLLEGE_URLS` for all RIT colleges.

### Phase 3: Collaboration Platform
- Defined `Idea` data model in `src/database/models.py`.
- Built `IdeaMatcher` in `src/collaboration/matcher.py` — AI-powered faculty matching.
- Added "Collaboration Hub" tab with idea submission form to `web_app.py`.
- Implemented interactive Prism graph visualization using `streamlit-agraph`.
- **Test:** `python tests/test_matcher.py` → PASS.

### Phase 4: AI Enhancements
- Implemented semantic query expansion (`src/chatbot/query_engine.py`) using Ollama.
- Built impact analyzer (`src/analysis/impact_analyzer.py`) scoring research ideas 1–10 on societal impact / UN SDG alignment.
- Integrated impact scoring into the Collaboration Hub.

### Phase 5: Advanced Interaction
- Created three AI personas: Tiger (Friendly), Analyzer (Technical), Critique (Critical).
- Added `set_persona()` method and `_load_persona_prompt()` with caching to `OllamaClient`.
- Persona selector added to the Streamlit sidebar.
- **Test:** `python tests/test_persona.py` → PASS.

### Overnight Build Summary
| Metric | Value |
|--------|-------|
| New Files Created | 11 |
| Files Modified | 6 |
| Lines of Code Added | ~1,500+ |
| New Dependencies | `streamlit-agraph` |
| AI Personas | 3 |
| Colleges Supported | 3+ |

---

## 5. Architecture Decision: V2 "TigerStack"

On **February 9, 2026**, we formally designed the V2 "Hybrid RAG" architecture — the "Two-Lobe Brain."

### The Two-Lobe Brain (Chosen Architecture)

```
User Query
    │
    ▼
Query Router
    ├──── Lobe 1: Vector Search (LanceDB) → Relevant Document Chunks
    │
    └──── Lobe 2: Graph Search (TigerBrain/NetworkX) → Relevant Subgraph
    
Both lobes feed a unified Synthesizer (LLM) → Final Answer
```

### Three Retrieval Strategies Considered

| Strategy | Mechanism | Decision |
|----------|-----------|----------|
| **Option A: Parallel "Two-Lobe"** | Both searches run concurrently | ✅ Chosen as baseline |
| **Option B: Sequential "Graph-First"** | Graph results filter vector search | ✅ Used for ENTITY queries |
| **Option C: Hybrid Adaptive Routing** | Query classifier selects strategy | ✅ Implemented (keyword-based classifier) |

### Architecture Clarifications (Locked decisions)
| Question | Answer |
|----------|--------|
| LLM Model | Qwen 2.5 (32B) via Ollama — local, open-weights |
| Latency Target | < 10 seconds (accuracy > speed) |
| Concurrency | Single-user initially; lab server (5–10 users) in future |
| Deployment | Local / On-Prem — privacy first, no external API calls |

### Scalability Risk Register
| Risk | Trigger Threshold | Mitigation |
|------|------------------|------------|
| NetworkX performance | 5k papers (>200ms p95) | Migrate to Memgraph/Neo4j |
| LLM token limits | Combined context > 8k tokens | Two-stage synthesis + context compression |
| Graph update conflicts | Multi-user write contention | Read-write locks or async update queue |

---

## 6. Migration Rationale: Why We Changed Everything

Each V1 component was replaced. Here is the documented reasoning:

### A. Scraper: `rit_crawler.py` → `SmartCrawler`
- **V1 Problem:** `BeautifulSoup` + hardcoded CSS selectors → broke when RIT changed a `div.bio` to `span.about`.
- **V2 Solution:** LLM-based semantic parsing. The model reads the page like a human; HTML structure changes don't matter.

### B. PDF Engine: Naive Chunking → `DeepDistiller`
- **V1 Problem:** Raw text chopped into 500-word chunks. The chunk *"results showed a 5% increase"* is meaningless without context.
- **V2 Solution:** `DeepDistiller` reads the entire paper (Abstract + Intro + Results) and asks the LLM to generate a structured **Research Card** — a dense semantic summary. We index the *thesis*, not fragments.

### C. Database: ChromaDB → LanceDB (planned)
- **V1 Problem:** ChromaDB was slow on metadata filtering; not optimized for local SSDs.
- **V2 Solution:** LanceDB — serverless, embedded, Apache Lance columnar format, optimized for Mac NVMe drives. Zero Docker overhead.

### D. Embeddings: `MiniLM` → `nomic-embed-text-v1.5` (planned)
- **V1 Problem:** 384 dimensions, 512 context window — truncated full research paper summaries.
- **V2 Solution:** `nomic-embed-text-v1.5` (Matryoshka embeddings, 8192 context window). Runs efficiently on Apple Silicon via Ollama.

### E. Intelligence: Keyword Search → Knowledge Graph (TigerBrain)
- **V1 Problem:** Similarity search only. Couldn't answer "Who collaborates with Prof X?" or "What is the biggest research cluster?"
- **V2 Solution:** NetworkX knowledge graph with `AUTHORED`, `MENTIONS`, and `INTERESTED_IN` edges. Enables GraphRAG — graph traversal + vector search.

---

## 7. Experiment 4 — The TigerBrain Knowledge Graph

**Date:** February 9, 2026 | **Status:** ✅ Complete

### Objective
Transition from a purely structural site graph (URLs → URLs) to a semantic knowledge graph (Concepts → Faculty → Papers).

### Three-Stage Construction Pipeline

**Stage 1: Data Ingestion**
- `SmartCrawler` → scraped RIT directory → **Faculty nodes** with Department/Title metadata.
- `DeepDistiller` (Qwen/TigerBuddy) → processed 1,145 PDF papers → structured **Research Cards** (title, authors, year, entities, relations).

**Stage 2: Graph Assembly (`graph_builder.py`)**
- Author Matching: `fuzzywuzzy` at >85% confidence to match "C. Kanan" → "Christopher Kanan".
- Node Types: Faculty (Blue), Paper (Green) via `[AUTHORED]`, Concept (Orange) via `[MENTIONS]`.

**Stage 3: Neural Refinement (`graph_refiner.py`)**
- Deduplication: merged synonymous concepts ("CNN" + "ConvNet" + "Convolutional Network" → single node).
- Taxonomy Generation: LLM analyzed top-50 concepts → generated Topic Cluster nodes (Purple) like "Computer Vision", "Deep Learning" linked via `[IS_A]` edges.

### Results

| Metric | Count |
|--------|-------|
| Total Nodes | 44,959 |
| Total Edges | 46,241 |
| Faculty Nodes | ~170 |
| Paper Nodes | 1,060 |
| Concept Nodes | ~43,000 |

### Key Learnings
1. **LLM > Regex:** Using LLM for Neural Refinement was critical — the raw graph was too noisy without deduplication.
2. **Hybrid is Best:** Neither the Site Graph nor the Research Graph alone was sufficient; merging them solidified the link between *People* and *Ideas*.
3. **Visualization Matters:** PyVis proved the graph is dense and highly interconnected, confirming RIT's research is collaborative.

---

## 8. v2.1 — Vision-First Ingestion

### The Data Quality Gap
`PyMuPDF` text extraction had critical limitations:
| Feature | PyMuPDF | VisionCrawler (Marker-PDF) |
|---------|---------|--------------------------|
| Layout | Linear text stream (mixes columns) | Layout-aware Markdown |
| Tables | Garbage characters | Markdown tables |
| Math | Garbled symbols | LaTeX formulas |
| Artifacts | Headers/footers included | Removed |

### The TigerCard 2.0 Schema
```json
{
  "bibliographic_data": { "title": "...", "primary_domain": "cs.CV", "authors": ["..."] },
  "core_content": {
    "novelty_claim": "...",
    "key_methodology": "...",
    "outcomes": ["3.57% error on ImageNet", "Won ILSVRC 2015"]
  },
  "knowledge_graph": {
    "nodes": [{"id": "residual_learning", "type": "Method"}],
    "edges": [{"source": "residual_learning", "target": "vanishing_gradient", "relation": "SOLVES"}]
  }
}
```

### Why 8k Context Window Is Critical
Standard 2k context truncates the schema instructions, leading to hallucination and schema drift. All LLM calls involving schema extraction now use `num_ctx: 8192`.

---

## 9. v2.2 — Fast-by-Default: Apple Silicon Optimization

### The Problem with Marker-PDF
Running full Marker-PDF (VLM) on every page was making PDF processing the system bottleneck.

### The Breakthrough: Smart Gating
The new `DocumentProcessor` (`--engine apple_fast`) uses a three-stage gate:
1. **Digital Gate:** Check for existing text layers (`min_digital_chars`). If found → millisecond extraction.
2. **Table Gate:** Heuristic scan → Surya Layout Analysis (MPS-accelerated) → GMFT table extraction.
3. **OCR Fallback:** `Surya` OCR on MPS backend (much faster than CPU Tesseract).

### Benchmark Results (February 16, 2026)

| Metric | Marker (Legacy) | apple_fast (New) | Improvement |
|--------|----------------|-----------------|-------------|
| Digital PDF Speed | 4.42s/page | 0.018s/page | **245× faster** |
| Mixed PDF Speed | 7.02s/page | 0.135s/page | **52× faster** |
| Throughput | 0.23 pg/s | ~56 pg/s | **High Scale** |

> The bottleneck successfully shifted from **PDF processing** to **network I/O**.

### Configuration Added

```bash
# Engine selection
python run_pipeline.py --engine apple_fast    # Default
python run_pipeline.py --engine marker        # Legacy VLM

# PDF rendering backend
--pdf-backend pymupdf     # Default (AGPL, best performance)
--pdf-backend pypdfium2   # Apache 2.0 (AGPL-free)

# Table extraction
--tables auto    # Default (heuristic + layout analysis)
--tables force   # Force on every page
--tables off     # Disable completely (fastest)
```

---

## 10. AI Architecture Reviews & The Final Implementation Plan

**Date:** February 9, 2026  
We asked five AI systems (ChatGPT, Claude, Gemini, Perplexity, Grok) to review our architecture. Here is what they universally agreed on, and what we actually implemented.

### Universal Consensus (All 5 AIs Agreed)
1. **Entity Resolution is CRITICAL** — `fuzzywuzzy >85%` will catastrophically fail at scale ("J. Smith" = 2 papers instead of 10).
2. **Adaptive Routing > Pure Parallel** — different query types need different strategies.
3. **RRF Fusion > Weighted Scores** — Reciprocal Rank Fusion is mathematically sound; prevents score incompatibility between graph centrality (unbounded) and vector similarity (0–1).
4. **Re-ranking is mandatory** — cross-encoder adds 20–40% precision boost.
5. **NetworkX will break at 5–10k papers** — plan migration to Memgraph/Neo4j.

### What We Chose to Ignore (Overengineering)
- Redis/Distributed Caching → use Python `@lru_cache` instead.
- Change Data Capture (CDC) pipelines → simple WAL pattern is fine.
- Community Detection (Louvain/Leiden) → not needed for our scale.
- FalkorDB → less mature than Memgraph/Neo4j.

### Implementation Phases Defined (Phased 4-Week Roadmap)

| Phase | Week | Goal | Status |
|-------|------|------|--------|
| 1.1 | 1 | Entity Resolution Pipeline (`entity_resolver.py`) | ✅ Implemented |
| 1.2 | 2 | Hybrid Retriever with Adaptive Routing | ✅ Implemented |
| 2.1 | 3 | Reciprocal Rank Fusion (`fusion.py`) | ✅ Implemented |
| 2.2 | 3 | Cross-Encoder Re-ranking | 🔲 Planned |
| 3.1 | 4 | `@lru_cache` for query results | 🔲 Planned |
| 3.2 | 4 | Structured logging + observability | ✅ Implemented |

### Graph DB Migration Trigger Plan
| Papers | Action |
|--------|--------|
| 1k–3k | Stay on NetworkX |
| 3k | Run `scripts/benchmark_graph.py` (measure p95 latency) |
| 5k OR >200ms p95 | **Migrate to Memgraph** |
| 10k | Mandatory migration (NetworkX will OOM) |

---

## 11. Entity Extraction Deep Dive

Entity extraction is the critical first step in the Sequential Retrieval path.

### Baseline: Pure Lexical Matching
- Build index: `{lowercase_label → node_id}` for all 48,182 entities.
- Check if any indexed label appears as a substring in the query.
- **Speed:** ~1ms | **Accuracy:** ~85% for exact matches.
- **Fails on:** "CNNs" ≠ "Convolutional Neural Networks", "vision research" → nothing.

### Strategy 1: LLM Fallback (Implemented)
```
extract(query):
  entities = _lexical_match(query)        # 1ms, 85% recall
  if len(entities) < 2:
      entities = _llm_fallback(query)     # ~150ms, 95% recall
  return entities
```
- **Hit rate:** 90% of queries use the fast lexical path.
- **Average latency:** ~16ms.

### Strategy 2: LLM Enrichment (Planned — For Exploratory Queries Only)
Always runs LLM enrichment — synonym expansion, disambiguation, inferred concepts.
- **Tradeoff:** 98% accuracy vs. 150ms always (vs. 16ms average with Strategy 1).
- **When to use:** Only for `QueryType.EXPLORATORY`.

---

## 12. Hybrid Retrieval: From Concept to Code

The `HybridRetriever` combines ChromaDB vector search with BM25 keyword search using Reciprocal Rank Fusion.

### Query Types and Strategies

| Query Type | Example | Strategy |
|------------|---------|----------|
| `ENTITY` | "Who works on X?" | Graph Traversal (Sequential) |
| `FACTOID` | "What is Zero-Shot Learning?" | Vector + BM25 (Parallel) |
| `RELATIONAL` | "Compare Prof X and Y" | Graph Pathfinding |
| `EXPLORATORY` | "What's new in robotics?" | Parallel + LLM Entity Enrichment |

### Reciprocal Rank Fusion (RRF)
```python
def reciprocal_rank_fusion(vector_results, bm25_results, k=60):
    """RRF score = Σ [1 / (k + rank(d))] across all rankers"""
    scores = defaultdict(float)
    for rank, result in enumerate(vector_results, start=1):
        scores[result['id']] += 1.0 / (k + rank)
    for rank, result in enumerate(bm25_results, start=1):
        scores[result['id']] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
```

**Why RRF?** Vector similarity (0–1) and BM25 scores are incomparable. RRF uses rank positions instead, making fusion mathematically sound regardless of scale differences.

---

## 13. Code Quality & Engineering Improvements

Over the course of the project we addressed multiple engineering concerns.

### Pipeline Runner (`run_pipeline.py`)
Created a robust, reusable orchestration script replacing ad-hoc stage scripts.

**Six stages:**
1. **Crawl** — harvest faculty profiles from RIT CS site.
2. **Scholar Enrichment** — add Google Scholar metrics (citations, h-index).
3. **Download** — pull PDFs from ArXiv & Semantic Scholar.
4. **Distill** — AI reads PDFs → structured Research Cards.
5. **Index** — embed all data into vector store (ChromaDB).
6. **Graph** — build knowledge graph (optional, needs Ollama).

**Key design:** Any stage can be skipped (`--skip-crawl`, `--skip-scholar`, etc.), and the pipeline gracefully loads from disk to allow partial reruns.

**Run modes:**
```bash
python run_pipeline.py --mode restricted    # Fast dev/test (~10 profiles)
python run_pipeline.py --mode full          # Full CS department (hours)
```

### Database Logging
Implemented structured logging to SQLite for every pipeline operation, enabling:
- Timing metrics per stage.
- Bottleneck identification via data mining.
- Unique operation IDs for traceability.

### Error Handling
Comprehensive `try/except` coverage added across all modules. Every operation logs errors without crashing the pipeline — failed stages are reported in the final summary table.

### Author Mismatch Fix
Debugged a critical bug in `_is_author_match()`: papers with last-name-only collisions were being downloaded despite the function returning `False`. Fixed pipeline logic that was bypassing the author filter.

### Web App Import Fix
Resolved a `NameError` caused by a missing `QueryEngine` import in `web_app.py`.

---

### Prompt Engineering (V2.0 Architecture)
A major refactor was performed on all AI prompt templates (`data/prompts/*.md`) to aggressively mitigate LLM hallucinations and enforce output verifiability. This included:
- **Strict Grounding:** Explicitly commanding the LLM to only answer from the provided `<Context>` and to declare missing information otherwise.
- **Explicit Citation Rules:** Forcing the LLM to state exactly where it found evidence within the generated response.
- **Defensive Structures:** Enforcing strict 'Sandwich' protocol (Validate, Tear-Down, Suggest) for critiques and mandatory markdown tables for metric comparisons to prevent data invention.
- **Chain of Density Polish:** Banning markdown wrappers around JSON outputs and forcing strict metric extraction during synthesis.

---

## 14. Challenges, Bugs & How We Fixed Them

### Codebase Analysis (February 10, 2026)
A formal audit identified **23 distinct issues** across 7 categories.

#### Critical Issues (Fixed)
| Issue | Problem | Fix Applied |
|-------|---------|-------------|
| Brittle Crawler | CSS selectors broke on RIT site updates | Migrated to SmartCrawler (LLM-based) |
| Missing 8k Context | Schema hallucinations in LLM extraction | Added `num_ctx: 8192` to all schema calls |
| Dependency Mismatches | `chromadb==0.4.22` required vs `1.4.1` installed | Upgraded dependencies; synced requirements |
| Author Filter Bug | Papers with last-name collisions bypassed filter | Fixed `_is_author_match` logic |

#### High Priority (Partially Fixed)
| Issue | Problem | Status |
|-------|---------|--------|
| Entity Resolution Edge Cases | "Flash Memory" ≠ "NAND Flash" | Improved fuzzy threshold to 90%; embedding-based merge planned |
| Async Crawling | Sequential requests with 0.5s sleeps | Multithreading added to scholar crawler |
| Insufficient Test Coverage | Many debug scripts, not real tests | Test script created; pytest coverage pending CI/CD |

#### Data Quality Wins
- **PDF multi-column layouts:** Resolved by v2.2 `apple_fast` engine with Surya layout analysis.
- **Crawler traps:** Manual delays + user-agent rotation.
- **Duplicate nodes:** `EntityResolver` fuzzy matching at 90% threshold + canonical ID system.

### Known Remaining Issues
- No conversational memory (user must repeat context).
- 5–10% citation hallucination rate in long contexts ("lost in the middle").
- Streamlit is single-threaded; not suitable for >10 concurrent users.
- LLM inference latency: 15–45s on unquantized models → use `q4_0` quantized builds.
- Context window fragments: strict top-5 result limit to stay within 8k tokens.

---

## 15. Brainstorming & Ideas Captured Along the Way

Ideas from AI agents, community feedback, and internal sessions, preserved for future work.

### From AI Community (Moltbook, Feb 2, 2026)
1. **AI Impact Analysis** — score papers on societal/ethical impact and UN SDG alignment (partially implemented as `ImpactAnalyzer`).
2. **Meaning-Based Discovery** — semantic query expansion, "related research" suggestions, show *why* results are relevant.
3. **Autonomous Social Presence** — TigerResearchBuddy posts daily research summaries to communities.
4. **Multi-Model Consensus** — compare Ollama + Gemini + Claude responses side-by-side.
5. **Security & Stability** — circuit breakers, graceful degradation, health-check endpoints.

### Internal Enhancement Ideas
6. **Personalized Research Roadmaps** — input student background & goals → curated sequence of papers, professors, labs.
7. **Research Trend Analysis** — weekly "hot topics" by counting new papers; faculty collaboration heatmaps.
8. **Office Hours Matching** — connect students with faculty based on research alignment + availability.
9. **Research Alerts** — subscribe to new papers, faculty talks, and opportunity postings in your interest areas.
10. **Cross-University Collaboration** — find similar research at other universities; link RIT researchers with potential external collaborators.

### Collaboration Platform Ideas
11. **AI Synergy Reports** — when a match is found (Biology + CS), generate a 1-page "Joint Proposal Starter" with potential grant titles and combined methodology.
12. **Resource & Equipment Matching** — match departments not just by ideas but by physical/digital assets ("Dept A has an HPC cluster, Dept B has a large dataset").
13. **Cross-Pollination Agent** — autonomous background agent that reads papers and proactively suggests interdisciplinary connections.
14. **The Prism — 3D Knowledge Graph** — upgrade 2D collaboration graph to a fully interactive 3D WebGL galaxy of research nodes.
15. **Automated Grant Scouting** — monitor Grants.gov/NSF.gov; alert researchers when grant matches a *combination* of departments' strengths.

### KnowledgeDaemon (Planned — Phase 5)
The `KnowledgeDaemon` is a background agent to solve the stale-data problem:
- **Watcher:** Detects new PDFs in `data/papers/` → runs `DeepDistiller` → updates graph automatically.
- **Auditor (Audrey):** Periodically scans for sparse nodes (e.g., faculty with no bio) → investigates → patches.
- **Critic:** On user feedback ("that answer was wrong") → traces source nodes → verifies → prunes false edges.

---

## 16. Future Roadmap

### Short-Term (v2.3)
- [ ] Migrate embeddings to `nomic-embed-text-v1.5` (higher quality, 8192 context).
- [ ] Migrate vector store from ChromaDB to LanceDB (10–100× faster local queries).
- [ ] Add Cross-Encoder re-ranking (20–40% precision boost with `bge-reranker-v2-m3`).
- [ ] Implement `@lru_cache` for query results (target: >40% hit rate).
- [ ] Add pytest coverage reporting and CI/CD pipeline.

### Medium-Term (v3.0)
- [ ] Multi-user support (FastAPI + stateless backend).
- [ ] KnowledgeDaemon (watcher + auditor loops).
- [ ] Interactive PyVis graph visualization in the UI.
- [ ] User feedback loop → graph quality scores.
- [ ] Docker packaging for lab server deployment.

### Long-Term Vision
- [ ] Migrate to Memgraph/Neo4j at 5k papers (per migration trigger plan).
- [ ] Multi-modal: index figures and charts from papers (vision model column).
- [ ] Cross-university collaboration discovery.
- [ ] Automated grant opportunity scouting.
- [ ] Mobile-responsive UI or progressive web app.

---

17. [External Architecture Review: Bottlenecks & Recommendations (Feb 2026)](#17-external-architecture-review-bottlenecks--recommendations-feb-2026)

---

## 17. External Architecture Review: Bottlenecks & Recommendations (Feb 2026)

_Generated: 2026-02-11 — Full bottleneck analysis for TigerBrain 2.0 (Hybrid RAG: Vector DB + Knowledge Graph + Local LLM)_

**Priority order for biggest wins:** (1) ingestion fidelity → (2) hybrid retrieval + reranking → (3) graph query scalability → (4) eval/observability.

### A. Retrieval Quality & Hybrid Search

**1. Weak precision on entity queries ("who works on X")**
- **Root cause:** Vector-only retrieval misses exact-name matches and multi-hop facts; embeddings blur entity identity.
- **Fixes:** ✅ BM25+vector hybrid with RRF. ✅ Query router (entity → graph-first; topical → vector-first). ✅ Canonical IDs + alias expansion.
- **Still needed:** Cross-encoder reranker on top_k=50 (AnswerDotAI/rerankers, FlagEmbedding bge-rerankers).

**2. Answer groundedness / citation drift**
- **Fixes:** Structure context: must-use evidence first, optional secondary. Internal cite-then-explain constraint. Citation-aware decoding — refuse unsupported claims.
- **Tools:** RAGAS / DeepEval for groundedness. Langfuse for trace inspection.

**3. Query-time latency spikes**
- **Fixes:** Two-stage retrieval (cheap BM25 → decide if graph expansion needed). Adaptive token budgeting per source. Cache query embeddings + final answers for repeated queries.

### B. Knowledge Graph: Entity Resolution & Taxonomy

**1. Duplicate / synonym nodes**
- **Status:** ✅ Canonical pipeline (normalize → fuzzy → LLM merge). ✅ Provenance tracking. **Still needed:** Blocking keys (last name + org, DOI, email) to avoid O(n²) comparisons.

**2. Taxonomy / ontology drift**
- **Fixes:** Version taxonomy snapshots. Separate schema (types/relations) from instance graph. Run community detection only on changed subgraphs.

**3. Graph expansion → irrelevant hops**
- **Fixes:** Score edges by co-occurrence, citation count, recency. Typed traversal rules per query intent. Max frontier + "stop condition".

### C. Graph Scalability

**1. NetworkX bottleneck at scale**
- **Threshold:** Migrate at >5k papers or p95 >200ms (see migration trigger plan, §10).
- **Recommended path:** **Kuzu** (embedded graph DB with Cypher + vector + full-text) as first step before Neo4j.

**2. Slow multi-hop queries / path explosion**
- **Fixes:** Cost-based traversal (limit expansions per hop, prefer high-confidence edges). Materialize "expertise subgraphs" per concept cluster.

### D. Ingestion: PDF Parsing & Chunking

**PDF parsing fidelity** — ✅ Resolved in v2.2 via `apple_fast` engine. Edge case: very old scanned docs → use `--engine marker`. Alternative: `docling-project/docling`.

**Chunking** — ✅ TigerCard 2.0 schema does document-level summarization instead of fixed-size chunks. For auxiliary indexes: chunk by section hierarchy (H1/H2).

**Missing metadata** — ✅ `bibliographic_data` extracted explicitly. Paper nodes have stable IDs.

### E. LLM Inference & Context

**Latency** — ✅ `q4_0` quantized model path. ✅ Streaming. **Still needed:** Smaller router model for intent classification; Qwen 2.5 for synthesis only.

**Context overflow** — ✅ Hard top-5 limit. **Improvement:** Token-aware packing with priorities (metadata → best chunks → graph facts).

### F. Evaluation, Regression Testing & Observability

- ✅ Full evaluation framework created: `docs/wiki/09_evaluation.md` + `tests/automated_evaluator.py`.
- **Still needed:** CI/CD gate (fail PR if canary score drops below threshold). Retrieval dossier per answer. Self-hosted Langfuse for trace inspection.

### G. Deployment & Ops

**Resource contention** — Background ingestion worker (KnowledgeDaemon Watcher). Incremental indexing — re-embed only changed docs.

**Index version mismatch** — Version indexes with `(embedding_model, chunker_version, parser_version)`. Migration scripts on upgrade.

### H. UX & Product

**Trust & provenance** — Citations + source snippets. Answer modes: strict (cited only), balanced, creative.

**Conversation state** — ✅ Not yet implemented. Fix: compact memory tracking entities mentioned + last retrieval set.

### I. Security & Privacy

**PII in logs** — Redact by default. Hash PII fields. "No telemetry" as first-class `.env` toggle.

### Reference Libraries

| Category | Recommended Repos |
|----------|-------------------|
| GraphRAG | `microsoft/graphrag`, `neo4j/neo4j-graphrag-python` |
| Reranking | `AnswerDotAI/rerankers`, `FlagOpen/FlagEmbedding` |
| Doc parsing | `datalab-to/marker`, `docling-project/docling` |
| Eval / LLMOps | `vibrantlabsai/ragas`, `confident-ai/deepeval`, `promptfoo/promptfoo`, `langfuse/langfuse` |

### Recommended Next Sprint (Highest ROI)

1. **Cross-encoder reranking** — `bge-reranker-v2-m3`, 20–40% precision boost.
2. **Graph edge weights** — score by co-occurrence + citation count; cap per-hop expansion.
3. **Eval + CI gate** — 200-question eval suite + Langfuse traces + PR score threshold.
4. **Conversation memory** — entity carry-forward across turns.

---

*This document is the single source of narrative truth for the TigerResearchBuddy project. For technical reference, see the wiki at `docs/wiki/`.  
For running the system, see `docs/wiki/06_deployment.md`.  
For evaluation and testing, see `docs/wiki/09_evaluation.md`.*
