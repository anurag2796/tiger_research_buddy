# TigerStack 2.0 Migration Plan: The Hybrid Architecture 🐅🚀

**Status**: Draft
**Date**: February 9, 2026
**Goal**: Transition from experimental scripts to a robust, production-ready "Hybrid RAG" system that combines **Vector Search** (LanceDB) with **Knowledge Graph Traversal** (TigerBrain).

---

## 1. Executive Summary
We have successfully built the components:
- **DeepDistiller**: Extracts deep semantic meaning from PDFs.
- **TigerBrain**: Constucts a knowledge graph of Faculty, Papers, and Concepts.
- **LanceDB**: Stores vector embeddings of chunks.

**Phase 2 Objective**: unify these into a single query pipeline. When a user asks "Who works on Zero-Shot Learning?", the system should:
1.  **Vector Search**: Find papers mentioning "Zero-Shot Learning".
2.  **Graph Search**: Find the "Zero-Shot Learning" node in TigerBrain and traverse edges to finding leading Faculty.
3.  **Synthesize**: Give a comprehensive answer citing both papers and faculty profiles.

---

## 2. Architecture: "The Two-Lobe Brain" 🧠

```mermaid
graph TD
    User[User Query] --> Router{Query Router}
    
    subgraph "Lobe 1: Vector Search (Semantic Similarity)"
        Router -->|Unstructured| Lance[LanceDB]
        Lance --> Docs[Relevant Chunks]
    end
    
    subgraph "Lobe 2: Graph Search (Structured Relations)"
        Router -->|Entities/Concepts| TB[TigerBrain (NetworkX)]
        TB --> Subgraph[Relevant Subgraph]
    end
    
    Docs --> Synthesizer[LLM Response Generator]
    Subgraph --> Synthesizer
    Synthesizer --> Final[Answer]
```

---

## 3. Implementation Steps

### Step 1: Core Refactoring (Cleanup) 🧹
*   **Move Experimental Scripts**: Move `distill_paper.py`, `graph_builder.py` into a proper package structure (e.g., `src/pipeline/`).
*   **Unified Config**: Create `config.py` to manage paths (`data/tiger_brain.gml`, `data/lancedb`) cleanly.

### Step 2: The `HybridRetriever` Class 🔍
Create `src/retrieval/hybrid_retriever.py`:
- **Input**: User Query
- **Logic**:
    1.  **Vector Search**: `lance_manager.search(query, k=5)`
    2.  **Keyword Extraction**: Use LLM to extract entities from query (e.g. "Zero-Shot Learning").
    3.  **Graph Traversal**: 
        - Find entity node in `TigerBrain`.
        - Get neighbors (Papers, Faculty).
        - Format as text context: `"Concept 'Zero-Shot Learning' is studied by Prof. Kanan in papers [P1, P2]..."`
- **Output**: Combined Context String.

### Step 3: The `ChatEngine` Upgrade 💬
Update `src/chatbot/chat.py` (or create `engine.py`):
- Replace simple LanceDB lookup with `HybridRetriever`.
- Update System Prompt to encourage using the Graph Context (e.g., "Use the provided graph relationships to explain connections.").

### Step 4: Automation (The "Watcher") 🤖
Create `src/pipeline/watcher.py`:
- Monitor `data/papers/` for new PDFs.
- On new file:
    1.  Run `DeepDistiller` -> Generate JSON.
    2.  Run `GraphBuilder.update()` -> Add nodes to Graph.
    3.  Run `LanceManager.add()` -> Add chunks to Vector DB.
- **Benefit**: "Drop a paper in the folder, and the brain grows."

---

## 4. Work Plan Checklist

- [ ] **1. Refactor**: Organize `src/` for production.
- [ ] **2. Implement `HybridRetriever`**:
    - [ ] Add `GraphSearch` class.
    - [ ] Combine with `LanceDB`.
- [ ] **3. Update Chatbot**:
    - [ ] Integrate new retriever.
    - [ ] Test with complex queries ("Who collaborates with X on Y?").
- [ ] **4. Automate Ingestion**:
    - [ ] Build the "Watcher" script.
