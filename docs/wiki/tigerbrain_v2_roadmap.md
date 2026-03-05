As the Lead AI Systems Engineer, I have reviewed the newly uploaded literature. The recent advancements in GraphRAG, Vision-Language Models (VLMs), and heterogeneous graph recommendations align perfectly with the bottlenecks we've identified in TigerBrain v2.2. 

Here is my synthesis of the literature and a concrete, actionable roadmap for upgrading our Hybrid RAG architecture.

### 1. Key Insights from the Literature

Based on the provided research, several technical breakthroughs are directly applicable to our current bottlenecks:

*   **Dual-Level Retrieval for Hybrid RAG:** The *LightRAG* architecture proves that splitting retrieval into "Low-Level" (specific entities and their immediate neighbors) and "High-Level" (broader abstract themes across multiple entities) significantly improves comprehensiveness and diversity of answers over traditional vector search. 
*   **Dependency Parsing for Efficient KG Construction:** Relying purely on LLMs for knowledge graph triplet extraction is computationally expensive. Research shows that integrating industrial-grade NLP dependency parsing (e.g., SpaCy) to extract subject-verb-object triples achieves 94% of LLM-based performance at a fraction of the cost.
*   **Relational-Aware Entity Resolution:** The literature on heterogeneous graph neural networks demonstrates that resolving author/entity ambiguities shouldn't rely solely on string similarity. Using the local graph topology (co-authors, shared topics, or venues) provides a much higher precision for disambiguating entities like "C. Kanan" vs. "Chris Kanan".
*   **Target Prompting for VLMs:** General prompting for Vision-Language Models often leads to hallucinated or missing data when reading complex documents. *Target Prompting*—explicitly cropping and targeting specific regions of a document (like a table or chart) with highly specific prompts—drastically reduces information gaps.
*   **Hypergraph & Centrality-Based Collaboration Discovery:** Treating research collaboration as a pairwise link prediction (Vector A to Vector B) misses the group dynamics of academia. Recommender systems perform much better when treating a research idea as a "query event" (hyperedge) and utilizing graph centrality metrics (like Personalized PageRank) to find interdisciplinary connections.

---

### 2. Targeted Architectural Upgrades

Here is how we map these insights directly into the TigerStack pipeline:

**The Deep Processing Phase (`pdf_distiller.py` & `entity_resolver.py`)**
Currently, `entity_resolver.py` relies on `fuzzywuzzy` string matching at a 90% threshold, which is risky at scale. We will upgrade this to a **Relational-Aware** approach. Before merging two similarly named nodes, the resolver will check their NetworkX neighborhoods to see if they share connected `Paper` or `Concept` nodes. 
For `pdf_distiller.py`, we will enhance the existing `apple_fast` smart gating system by integrating **Target Prompting**. When the layout parser detects a chart or table, instead of sending the whole page to the VLM, we will crop the bounding box and apply a targeted extraction prompt to preserve mathematical and tabular fidelity.

**The Hybrid Retrieval Layer (`hybrid_retriever.py`)**
We will implement **Dual-Level Retrieval** inspired by LightRAG and MiniRAG. The `QueryEngine` will be modified to prompt Ollama to extract both *low-level keys* (e.g., "Christopher Kanan") and *high-level keys* (e.g., "Deep Learning"). Low-level keys will be routed to our BM25/Vector search for exact matching, while high-level keys will trigger a 2-hop NetworkX community traversal. We will fuse both streams using our existing Reciprocal Rank Fusion (RRF) logic.

**The Collaboration Matcher (`matcher.py`)**
We will move beyond basic LanceDB/ChromaDB cosine similarity for matching student ideas to faculty. By implementing **Topology-Enhanced Recommendation**, we will map the student's idea tags directly to `Concept` nodes in TigerBrain. We will then run a Personalized PageRank (PPR) algorithm outward from those concepts to find `Faculty` nodes that serve as interdisciplinary hubs, fusing this graph score with the semantic vector score.

---

### 3. Actionable Implementation Plan

Here are 4 highly specific engineering tasks to assign for our next sprint:

**Task 1: Implement Relational-Aware Entity Deduplication**
*   **Source Inspiration:** "Author name disambiguation based on heterogeneous graph neural network" and "Architectural Evolution of TigerResearchBuddy".
*   **Proposed Change:** Upgrade `entity_resolver.py` to use graph context alongside fuzzy matching.
*   **Implementation:** In `EntityResolver`, when a fuzzy string match is between 80% and 95% (an ambiguous zone), fetch the 1-hop NetworkX neighbors for both candidate nodes (e.g., co-authors, departments, concepts). Calculate the Jaccard similarity of their neighbor sets. If the overlap exceeds a strict threshold, merge the canonical IDs; otherwise, keep them distinct. 

**Task 2: Dual-Level Query Expansion**
*   **Source Inspiration:** "LightRAG: Simple and Fast Retrieval-Augmented Generation".
*   **Proposed Change:** Modify `query_engine.py` to generate hierarchical search keys for the `HybridRetriever`.
*   **Implementation:** Update the `OllamaClient` prompt within the Query Engine to return a JSON object with `"high_level_keywords"` and `"low_level_keywords"`. Pass the low-level keywords to the BM25 index, and pass the high-level keywords to ChromaDB and a new `nx.ego_graph(G, radius=2)` traversal function to grab broader structural context.

**Task 3: VLM Target Prompting for Tables & Figures**
*   **Source Inspiration:** "Target Prompting for Information Extraction with Vision Language Model" and "SmolDocling/MinerU2.5".
*   **Proposed Change:** Upgrade the `apple_fast` engine in `pdf_distiller.py` to isolate complex visual elements.
*   **Implementation:** When the Surya layout parser identifies a `Table` or `Figure` block, crop that specific bounding box as an isolated image. Pass *only* that cropped image to the local VLM (or GMFT fallback) with a targeted prompt (e.g., "Extract only the raw Markdown data from this table, ignoring surrounding text"). Append this clean data to the TigerCard 2.0 schema.

**Task 4: PageRank-Enhanced Collaboration Matching**
*   **Source Inspiration:** "Smart Recommendation Engines for Interdisciplinary Research".
*   **Proposed Change:** Upgrade `IdeaMatcher.match_idea()` in `matcher.py` to include graph centrality.
*   **Implementation:** Extract the `tags` from the submitted `Idea` object. Find the corresponding `Concept` nodes in the NetworkX graph. Run `nx.pagerank()` using those concept nodes as the `personalization` dictionary. Sort the resulting `Faculty` nodes by their PageRank scores, normalize them, and fuse them via RRF with the baseline ChromaDB semantic similarity scores.