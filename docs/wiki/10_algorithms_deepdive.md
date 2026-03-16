# 10 - Algorithms & Complex Logic Deep Dive

**Last Updated:** March 9, 2026  
**Purpose:** Detailed mathematical and algorithmic breakdown of the complex mechanisms running inside TigerBrain.

---

## 1. Hybrid Search via Reciprocal Rank Fusion (RRF)

**Module:** `src/retrieval/hybrid_retriever.py`

When querying the knowledge platform, the system performs semantic Vector Search alongside keyword-based BM25 search. Combining these two different ranking paradigms is complex because their score scales are incompatible (e.g. cosine distance vs probabilistic term frequency). To solve this, the system implements **Reciprocal Rank Fusion (RRF)**.

### The Algorithm
For any given query, the retriever evaluates:
1. **Vector Set ($V$)**: Top $k$ documents returned by ChromaDB.
2. **BM25 Set ($B$)**: Top $k$ documents returned by Okapi BM25 algorithm.

Instead of comparing absolute scores, RRF assigns a new score to each document $d$ based on its **rank position** in each result list:
$$ RRF\_Score(d) = \sum_{r \in R} \frac{1}{k_{rrf} + \text{rank}(d, r)} $$
Where:
- $R$ is the set of rankers ($V$ and $B$).
- $k_{rrf}$ is a smoothing constant (set to `60` in TigerBrain).
- $\text{rank}(d, r)$ is the 0-indexed position of document $d$ in ranker $r$'s list.

### Why it works
- **Scale Independence**: Solves the problem of vector distances being bounded `[0,1]` while BM25 scores can scale infinitely.
- **Outlier Mitigation**: The constant $k=60$ limits the hyper-inflation of being `Rank 1` in a single irrelevant list, enforcing a preference for documents that score well across *both* paradigms.

---

## 2. Entity Resolution & Canonical Mapping

**Module:** `src/knowledge_graph/entity_resolver.py`

Raw academic metadata contains dirty author strings (e.g. `He, Kaiming`, `K. He`, `Kaiming He`). `EntityResolver` groups these into canonical nodes (`faculty_kaiming_he`) to prevent network fragmentation.

### The Resolution Tiers

The algorithm processes incoming strings through multiple confidence tiers:

1. **Exact Dictionary Match (Tier 0)**: Immediate mapping using the known canonical dictionary.
2. **Fuzzy String Match (Tier 1)**: Evaluates Levenshtein distance using `TheFuzz`. If similarity $> 95\%$, the string is merged immediately.
3. **Relational-Aware Jaccard Fallback (Tier 2)**: If fuzzy match sits in the ambiguous zone ($80\% - 95\%$), the algorithm relies on graph traversal to verify identity:
   - Identifies the 1-hop neighborhood for both the candidate node and the existing graph node.
   - Calculates the **Jaccard Similarity** of these neighborhoods:
     $$ J(A, B) = \frac{|A \cap B|}{|A \cup B|} $$
   - If $J(A, B) \geq 0.4$ (meaning they share at least 40% of their co-authors, published departments, or cited concepts), the ambiguous name is merged. Otherwise, it is kept distinct.

---

## 3. Cognitive Extraction Fallback Logic

**Module:** `src/processors/pdf_distiller.py`

Relying purely on Heavy Vision-Language Models (VLMs) is too slow for parsing hundreds of PDFs. The `DeepDistiller` uses a smart-gating algorithm to optimize speed without losing geometric structural data (like tables/figures).

1. **Digital Text Gate**: Reads PDF bytes to check for `\u0000` text length $> 50$ chars. If detected, PyMuPDF pulls the text in $\sim 18\text{ms}$.
2. **Tabular Geometry Gate**: Heuristics check for grid-line rendering elements in the PDF structural tree. If found, Surya Layout analysis detects bounding boxes, and GMFT strictly extracts tables to preserve cell shapes ($\sim 50\text{ms}$).
3. **Heavy OCR Fallback**: If the document is purely a scanned image, it is routed to the MPS-accelerated Surya OCR node ($\sim 135\text{ms}$).

### Asynchronous LLM Token Distillation

Once extracted, the raw text is truncated to a safe `15,000` character limit (approx `3,000` tokens). 
It relies on an `asyncio.Semaphore` (concurrency limit = 3) when invoking the local LLM. This prevents multiple massive concurrent matrix multiplications from crashing the Apple Silicon Unified Memory limits (OOM errors) while maximizing throughput payload via batch processing.
