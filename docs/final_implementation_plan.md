# TigerStack 2.0: Final Implementation Plan (Synthesis of 5 AI Reviews)

**Date:** February 9, 2026  
**Context:** Synthesized from architectural reviews by ChatGPT, Claude, Gemini, Perplexity, and Grok  
**Constraints:**
- **LLM:** Qwen 2.5 (32B) via Ollama (Local)
- **Latency Target:** <10 seconds (Accuracy > Speed)
- **Scale:** Single-user, 1,145 papers → 10k papers (future)
- **Deployment:** Local / On-Prem (Privacy First)

---

## Executive Summary: What All 5 Reviews Agreed On

### ✅ Universal Consensus
1. **Entity Resolution is CRITICAL** (Gemini's insight) - Your current `fuzzywuzzy` will catastrophically fail at scale
2. **Adaptive Routing > Pure Parallel** (All reviews) - Different query types need different strategies
3. **RRF Fusion > Weighted Scores** (Gemini/Perplexity) - Mathematically sound, prevents score incompatibility
4. **Re-ranking is mandatory** (All reviews) - Cross-encoder adds 20-40% precision boost
5. **NetworkX will break at 5-10k papers** (All reviews) - Plan migration to Memgraph/Neo4j

### ❌ What to IGNORE (Overengineering for Your Scale)
- Redis/Distributed Caching (use Python `@lru_cache`)
- Change Data Capture (CDC) pipelines (use simple WAL pattern)
- Community Detection (Louvain/Leiden) - Not needed
- FalkorDB (less mature than Memgraph/Neo4j)

---

## Phase 1: Foundation (Weeks 1-2) - **MUST DO**

### 1.1 Entity Resolution Pipeline (Week 1 - HIGHEST PRIORITY)

**Problem:** Your current `fuzzywuzzy >85%` will create this disaster:
```
"J. Smith" (Paper 1, 2)
"John Smith" (Paper 3, 4, 5, 6, 7)
"J. A. Smith" (Paper 8, 9, 10)
→ Query: "Who works on Zero-Shot Learning?" 
→ Returns 2 papers instead of 10!
```

**Solution: Canonical Entity System**

#### Implementation
Create `src/knowledge_graph/entity_resolver.py`:

```python
from fuzzywuzzy import process
from pathlib import Path
import json

class EntityResolver:
    """Resolve entity aliases to canonical forms"""
    def __init__(self, graph_path):
        self.canonical_map = {}  # {alias: canonical_id}
        self.canonical_entities = {}  # {canonical_id: entity_data}
        self.load_or_create_mappings()
    
    def resolve_author(self, raw_name: str, affiliation: str = None, coauthors: list = None) -> str:
        """Resolve author name to canonical ID"""
        # Step 1: Exact match
        if raw_name in self.canonical_map:
            return self.canonical_map[raw_name]
        
        # Step 2: Fuzzy match (with context)
        candidates = list(self.canonical_entities.values())
        
        # Build context-aware similarity score
        matches = []
        for canonical in candidates:
            score = process.extractOne(raw_name, canonical['aliases'])[1]
            
            # Boost score if affiliation matches
            if affiliation and affiliation == canonical.get('affiliation'):
                score += 10
            
            # Boost if coauthors overlap
            if coauthors and set(coauthors) & set(canonical.get('coauthors', [])):
                score += 5
            
            matches.append((canonical['id'], score))
        
        best_match = max(matches, key=lambda x: x[1])
        
        # Threshold: 90% (higher than your current 85%)
        if best_match[1] > 90:
            self.canonical_map[raw_name] = best_match[0]
            return best_match[0]
        
        # Step 3: Create new canonical entity
        new_id = f"faculty_{len(self.canonical_entities):04d}"
        self.canonical_entities[new_id] = {
            'id': new_id,
            'canonical_name': raw_name,
            'aliases': [raw_name],
            'affiliation': affiliation,
            'coauthors': coauthors or []
        }
        self.canonical_map[raw_name] = new_id
        return new_id
    
    def save_mappings(self):
        """Persist canonical mappings"""
        with open('data/entity_mappings.json', 'w') as f:
            json.dump({
                'canonical_map': self.canonical_map,
                'canonical_entities': self.canonical_entities
            }, f, indent=2)
```

#### Update `graph_builder.py`
```python
# Replace your current fuzzywuzzy logic
from entity_resolver import EntityResolver

class GraphBuilder:
    def __init__(self):
        ...
        self.entity_resolver = EntityResolver(self.data_dir)
    
    def merge_research_cards(self):
        """Updated author linking"""
        for author in normalized_authors:
            # Get affiliation + coauthors for context
            affiliation = card.get("institution", "")
            coauthors = [a for a in normalized_authors if a != author]
            
            # Resolve to canonical ID
            canonical_id = self.entity_resolver.resolve_author(
                author, affiliation, coauthors
            )
            
            # Link to canonical faculty node
            if canonical_id in self.graph:
                self.graph.add_edge(canonical_id, paper_id, type="AUTHORED")
```

**Deliverable:** Update 1,145 existing papers with canonical entity IDs

---

### 1.2 Hybrid Retriever with Adaptive Routing (Week 2)

**Architecture Decision:** Implement Gemini's "Adaptive Router" pattern

#### Create `src/retrieval/hybrid_retriever.py`

```python
from enum import Enum
from typing import List, Dict
import re

class QueryType(Enum):
    FACTOID = "factoid"  # "What is Zero-Shot Learning?"
    ENTITY = "entity"    # "Who works on X?"
    RELATIONAL = "relational"  # "Compare A and B"
    EXPLORATORY = "exploratory"  # "What's new in Y?"

class HybridRetriever:
    """Adaptive retrieval: Route by query type"""
    
    ENTITY_KEYWORDS = ["who", "which faculty", "researcher", "author", "professor"]
    FACTOID_KEYWORDS = ["what is", "define", "explain", "how does"]
    COMPARE_KEYWORDS = ["compare", "difference", "versus", "vs"]
    
    def __init__(self, vector_db, graph):
        self.vector_db = vector_db
        self.graph = graph
    
    def classify_query(self, query: str) -> QueryType:
        """Simple keyword-based classification"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in self.FACTOID_KEYWORDS):
            return QueryType.FACTOID
        elif any(kw in query_lower for kw in self.ENTITY_KEYWORDS):
            return QueryType.ENTITY
        elif any(kw in query_lower for kw in self.COMPARE_KEYWORDS):
            return QueryType.RELATIONAL
        else:
            return QueryType.EXPLORATORY
    
    def retrieve(self, query: str) -> Dict:
        """Main retrieval entry point"""
        query_type = self.classify_query(query)
        
        if query_type == QueryType.FACTOID:
            # Parallel: Speed matters for definitions
            return self._parallel_retrieve(query)
        else:
            # Sequential: Precision matters for research queries
            return self._sequential_retrieve(query)
    
    def _sequential_retrieve(self, query: str) -> Dict:
        """Graph-guided sequential retrieval"""
        # Step 1: Extract entities (use graph's concept index)
        entities = self._extract_entities_fast(query)
        
        # Step 2: Graph traversal
        graph_results = self._graph_search(entities, max_hops=2)
        paper_ids_from_graph = [n['id'] for n in graph_results if n['type'] == 'Paper']
        
        # Step 3: Vector search (EXCLUDE papers already found by graph)
        vector_results = self.vector_db.search(
            query, 
            k=20,
            filter={"id": {"$nin": paper_ids_from_graph}}  # Deduplication
        )
        
        return {
            'graph_results': graph_results,
            'vector_results': vector_results,
            'strategy': 'sequential'
        }
    
    def _parallel_retrieve(self, query: str) -> Dict:
        """Parallel retrieval for simple queries"""
        graph_results = self._graph_search([query], max_hops=1)
        vector_results = self.vector_db.search(query, k=10)
        
        return {
            'graph_results': graph_results,
            'vector_results': vector_results,
            'strategy': 'parallel'
        }
    
    def _extract_entities_fast(self, query: str) -> List[str]:
        """Fast entity extraction using pre-built index (NOT LLM)"""
        # Use your graph's concept nodes as a lookup dictionary
        concept_index = {c.lower(): c for c in self.graph.nodes if self.graph.nodes[c].get('type') == 'Concept'}
        
        # Find concepts mentioned in query
        entities = []
        for token in query.split():
            token_clean = token.lower().strip('.,?!')
            if token_clean in concept_index:
                entities.append(concept_index[token_clean])
        
        return entities
```

**Why This Works:**
- **No LLM for entity extraction** (0.5-2s saved per query)
- **Deduplication built-in** (sequential strategy excludes graph results from vector search)
- **Adaptive** (fast for definitions, precise for research queries)

---

## Phase 2: Fusion & Quality (Week 3)

### 2.1 Reciprocal Rank Fusion (RRF)

**Why RRF > Weighted Scores:** Vector similarity (0-1) and graph centrality (unbounded) are incomparable. RRF uses rank positions instead.

#### Create `src/retrieval/fusion.py`

```python
from collections import defaultdict

def reciprocal_rank_fusion(vector_results, graph_results, k=60):
    """
    Gemini's RRF algorithm
    Formula: RRF(d) = Σ [1 / (k + rank(d))]
    """
    scores = defaultdict(float)
    
    # Add vector ranks
    for rank, result in enumerate(vector_results, start=1):
        scores[result['id']] += 1.0 / (k + rank)
    
    # Add graph ranks
    for rank, result in enumerate(graph_results, start=1):
        scores[result['id']] += 1.0 / (k + rank)
    
    # Sort by RRF score
    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{'id': doc_id, 'rrf_score': score} for doc_id, score in merged[:20]]
```

### 2.2 Cross-Encoder Re-ranking

```python
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self):
        # Lightweight cross-encoder (fast enough for local use)
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    def rerank(self, query: str, candidates: List[Dict], top_k=5) -> List[Dict]:
        """Final precision boost"""
        # Prepare (query, doc) pairs
        pairs = [(query, c['text']) for c in candidates]
        
        # Score with cross-encoder
        scores = self.model.predict(pairs)
        
        # Re-sort by scores
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in ranked[:top_k]]
```

#### Update `HybridRetriever`
```python
class HybridRetriever:
    def __init__(self, vector_db, graph):
        ...
        self.reranker = Reranker()
    
    def retrieve(self, query: str) -> List[Dict]:
        """Complete pipeline"""
        raw_results = self._sequential_retrieve(query)  # or parallel
        
        # Step 1: RRF Fusion
        fused = reciprocal_rank_fusion(
            raw_results['vector_results'],
            raw_results['graph_results']
        )
        
        # Step 2: Re-rank top 20
        final = self.reranker.rerank(query, fused, top_k=5)
        return final
```

---

## Phase 3: Operationalization (Week 4)

### 3.1 Simple Caching (Python Built-in)

```python
from functools import lru_cache
import hashlib

class CachedRetriever:
    def __init__(self, retriever):
        self.retriever = retriever
    
    @lru_cache(maxsize=500)
    def _cached_retrieve(self, query_hash: str):
        """Cache by normalized query"""
        return self.retriever.retrieve(query_hash)
    
    def retrieve(self, query: str):
        # Normalize query for cache hits
        normalized = query.lower().strip()
        query_hash = hashlib.sha256(normalized.encode()).hexdigest()
        return self._cached_retrieve(query_hash)
```

### 3.2 Observability (Structured Logging)

```python
import structlog
import time

logger = structlog.get_logger()

class InstrumentedRetriever:
    def retrieve(self, query: str):
        with logger.contextualize(query=query):
            t0 = time.time()
            
            # Entity extraction
            entities = self._extract_entities_fast(query)
            logger.info("entity_extraction", latency=time.time()-t0, count=len(entities))
            
            # Graph search
            t1 = time.time()
            graph_results = self._graph_search(entities)
            logger.info("graph_search", latency=time.time()-t1, nodes=len(graph_results))
            
            # Vector search
            t2 = time.time()
            vector_results = self.vector_db.search(query)
            logger.info("vector_search", latency=time.time()-t2, chunks=len(vector_results))
            
            # Total
            logger.info("retrieval_complete", total_latency=time.time()-t0)
            
            return {'graph': graph_results, 'vector': vector_results}
```

---

## Migration Trigger Plan (Perplexity's Timeline)

| Papers | Action | Why |
|--------|--------|-----|
| **1k-3k** | Stay on NetworkX | Current setup is fine |
| **3k** | Run benchmark script | Measure p95 graph query latency |
| **5k OR >200ms p95** | **Migrate to Memgraph** | NetworkX will start degrading |
| **10k** | Mandatory migration | NetworkX will crash |

### Benchmark Script (Create `scripts/benchmark_graph.py`)

```python
import networkx as nx
import time

def benchmark_graph_queries(graph_path, num_queries=100):
    """Measure graph performance"""
    G = nx.read_gml(graph_path)
    
    latencies = []
    for i in range(num_queries):
        concept_node = f"concept_{i % 100}"
        
        t0 = time.time()
        # Simulate "Who works on X?" query
        neighbors = list(G.neighbors(concept_node))
        faculty = [n for n in neighbors if G.nodes[n].get('type') == 'Faculty']
        latencies.append(time.time() - t0)
    
    p50 = sorted(latencies)[len(latencies)//2]
    p95 = sorted(latencies)[int(len(latencies)*0.95)]
    
    print(f"Graph Query Latency:")
    print(f"  p50: {p50*1000:.1f}ms")
    print(f"  p95: {p95*1000:.1f}ms")
    
    if p95 > 0.2:  # 200ms
        print("⚠️  WARNING: Approaching migration threshold!")
```

---

## Implementation Checklist

### ✅ Week 1: Entity Resolution (CRITICAL)
- [ ] Create `src/knowledge_graph/entity_resolver.py`
- [ ] Update `graph_builder.py` to use canonical IDs
- [ ] Run on existing 1,145 papers
- [ ] Save `data/entity_mappings.json`

### ✅ Week 2: Hybrid Retriever
- [ ] Create `src/retrieval/hybrid_retriever.py`
- [ ] Implement query classifier
- [ ] Build sequential retrieval path
- [ ] Add fast entity extraction (no LLM)

### ✅ Week 3: Fusion & Re-ranking
- [ ] Create `src/retrieval/fusion.py` (RRF)
- [ ] Add cross-encoder re-ranker
- [ ] Integrate into `HybridRetriever`
- [ ] Test on 10 complex queries

### ✅ Week 4: Operationalization
- [ ] Add `@lru_cache` to retriever
- [ ] Add structured logging
- [ ] Create benchmark script
- [ ] Document decision in Decision Log

---

## What NOT to Do (Avoiding Overengineering)

1. ❌ **Don't** use Redis for caching (Python `lru_cache` is enough)
2. ❌ **Don't** implement CDC pipelines (simple file watcher is fine)
3. ❌ **Don't** add community detection (you don't need it)
4. ❌ **Don't** migrate to Neo4j yet (wait for 5k papers)
5. ❌ **Don't** use LLM for entity extraction (use graph index)

---

## Success Metrics

| Metric | Baseline (Current) | Target (Week 4) |
|--------|-------------------|-----------------|
| **Entity Resolution Accuracy** | ~85% (fuzzywuzzy) | >95% (canonical + context) |
| **Query Latency (p50)** | ? (unmeasured) | <5s |
| **Query Latency (p95)** | ? (unmeasured) | <10s |
| **Answer Precision** | ? (no reranking) | +30% (with cross-encoder) |
| **Cache Hit Rate** | 0% (no cache) | >40% (for FAQ queries) |

---

## Final Architecture Diagram

```mermaid
graph TD
    Query[User Query] --> Router{Query Classifier}
    
    Router -->|Factoid| Parallel[Parallel Strategy]
    Router -->|Entity/Relational| Sequential[Sequential Strategy]
    
    Sequential --> EntityExtract[Fast Entity Extraction<br/>Graph Index Lookup]
    EntityExtract --> GraphSearch[Graph Traversal<br/>NetworkX / Memgraph]
    GraphSearch --> VectorSearch[Vector Search<br/>LanceDB w/ Dedup Filter]
    
    Parallel --> ParallelGraph[Graph Search]
    Parallel --> ParallelVector[Vector Search]
    
    VectorSearch --> RRF[RRF Fusion]
    ParallelGraph --> RRF
    ParallelVector --> RRF
    
    RRF --> Rerank[Cross-Encoder<br/>Re-ranker]
    Rerank --> Cache{Cache?}
    Cache -->|Miss| LLM[Qwen 2.5 32B]
    Cache -->|Hit| Answer[Answer]
    LLM --> Answer
    
    style EntityExtract fill:#c8e6c9
*    style RRF fill:#fff9c4
    style Rerank fill:#ffecb3
    style Cache fill:#f3e5f5
```

---

This plan is **pragmatic, actionable, and tailored to your constraints**. It takes the best ideas from all 5 reviews while cutting out the enterprise-scale complexity.

**Start with Week 1 (Entity Resolution)** - it's the foundation everything else depends on. 🎯
