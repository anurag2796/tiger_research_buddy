# TigerStack 2.0: Architecture Discussion & Decision Log

**Status**: Active Discussion  
**Date**: February 9, 2026  
**Objective**: Evaluate architectural approaches for the v2 Hybrid RAG system and finalize the implementation plan.

---

## 1. Core Architectural Decision: Retrieval Strategy

### Option A: Parallel "Two-Lobe" Retrieval (Current Plan)
**How it works:**
1. Query arrives → Split to both retrievers simultaneously
2. Vector Search (LanceDB) → Returns Top-K document chunks
3. Graph Search (TigerBrain) → Extracts entities → Returns subgraph context
4. Synthesizer (LLM) → Combines both contexts → Generates answer

**Pros:**
- ✅ Fast: Both searches happen concurrently
- ✅ Comprehensive: Gets both semantic similarity AND structured relationships
- ✅ Resilient: If one lobe fails, the other still provides context

**Cons:**
- ❌ Redundancy: Might fetch overlapping information
- ❌ Context bloat: Sending both results to LLM uses more tokens
- ❌ Complexity: Need to merge/deduplicate results

### Option B: Sequential "Graph-First" Retrieval
**How it works:**
1. Extract entities from query → Search graph
2. Use graph results to refine vector search (e.g., filter by relevant papers/faculty)
3. Return focused results

**Pros:**
- ✅ Focused: Vector search is narrowed by graph context
- ✅ Efficient: Smaller context window for LLM
- ✅ Explainable: Clear reasoning path (Graph → Papers → Answer)

**Cons:**
- ❌ Slower: Sequential operations add latency
- ❌ Brittle: If entity extraction fails, whole pipeline breaks
- ❌ Limited: Misses semantic matches outside the graph's explicit relations

### Option C: Hybrid Adaptive Routing
**How it works:**
1. Query classifier determines query type:
   - Entity-focused ("Who works on X?") → Graph-first
   - Concept-focused ("How does X work?") → Vector-first
   - Exploratory ("What's new in Y?") → Parallel
2. Route accordingly

**Pros:**
- ✅ Optimal: Each query gets the best retrieval strategy
- ✅ Scalable: Can add more routing rules

**Cons:**
- ❌ Complex: Requires training/maintaining a query classifier
- ❌ Debugging: Harder to trace which path was taken

---

## 2. Scalability Risks

### Risk 1: NetworkX Performance at Scale
**Problem**: NetworkX is in-memory. At 10k papers (~100k+ nodes), graph operations might slow down.

**Mitigation Options:**
- [ ] **Indexing**: Add node/edge indices for common queries
- [ ] **Graph DB Migration**: Move to Neo4j or KuzuDB for production
- [ ] **Subgraph Caching**: Pre-compute common subgraph queries (e.g., "All papers by Faculty X")

### Risk 2: Graph Update Conflicts
**Problem**: If new papers are added during a query, the graph might be in an inconsistent state.

**Mitigation Options:**
- [ ] **Read-Write Lock**: Block reads during graph updates
- [ ] **Versioning**: Maintain graph snapshots, queries use stable versions
- [ ] **Async Updates**: Queue updates, apply during low-traffic windows

### Risk 3: LLM Token Limits
**Problem**: Combined context (Vector + Graph) might exceed LLM token limits.

**Mitigation Options:**
- [ ] **Smart Truncation**: Prioritize graph context over vector results
- [ ] **Two-Stage Synthesis**: Summarize vector results first, then combine with graph
- [ ] **Context Compression**: Use LLM to compress context before final generation

---

## 3. Missing Pieces (Quick Wins)

- [ ] **Caching Layer**: Cache frequent queries (e.g., "Who works on AI?")
- [ ] **Re-ranking**: After retrieval, re-rank results by relevance before sending to LLM
- [ ] **Query Expansion**: Expand user queries with synonyms (e.g., "ML" → "Machine Learning")
- [ ] **Logging & Metrics**: Track query latency, cache hit rates, graph traversal times
- [ ] **Fallback Strategy**: If graph is unavailable, gracefully degrade to vector-only

---

## 4. Clarifications (Architecture Context)
*Added to address reviewer questions.*

| Question | Answer |
| :--- | :--- |
| **1. LLM Model?** | **Qwen 2.5 (32B)** running locally via Ollama. It has excellent reasoning capabilities for its size. We might upgrade to Llama 3 or Mistral Large if needed, but we are committed to open weights. |
| **2. Latency Target?** | **< 10 seconds** for complex queries. Since this is a research assistant, accuracy > speed. Users are willing to wait for a "deep thought" answer. |
| **3. Concurrency?** | **Single-User** initially (Personal Local Tool). Future scaling to a Lab Server (5-10 concurrent users) is a nice-to-have but not immediate blocker. |
| **4. Deployment?** | **Local / Edge Server**. All data (PDFs, Embeddings, Graph) stays on-prem. No external API calls (privacy first). |

---

## 5. Decision Log

| Decision | Chosen Option | Rationale | Date |
|----------|---------------|-----------|------|
| *TBD* | *TBD* | *TBD* | *TBD* |

---

## 6. Next Steps

Once we finalize the architecture:
1. Update `docs/plan_v2_migration.md` with chosen approach
2. Create implementation tickets in `task.md`
3. Begin refactoring (Step 1: Cleanup)
