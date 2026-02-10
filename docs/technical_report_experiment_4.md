# Technical Report: Experiment 4 (TigerBrain Knowledge Graph) 🐅🧠

**Date:** February 9, 2026
**Status:** ✅ Complete
**Artifacts:** 
- `data/tiger_brain.gml` (Raw Graph)
- `data/tiger_brain_refined.gml` (Refined Graph)
- `data/tiger_brain_viz.html` (Visualization)

## 1. Objective
The goal was to transition from a purely **Structural Site Graph** (URLs linked to URLs) to a **Semantic Knowledge Graph** (Concepts linked to Faculty/Papers). This allows the system to answer queries like "Who works on Zero-Shot Learning?" even if that exact phrase isn't on a faculty profile page.

## 2. Methodology ("The Hybrid Approach")

We implemented a three-stage pipeline to construct the graph:

### Stage 1: Data Ingestion (The Foundation)
1.  **Site Graph**: We used `SmartCrawler` to scrape RIT's directory, extracting **Faculty** nodes and their Department/Title metadata.
2.  **Research Distillation**: We used `DeepDistiller` (powered by Qwen/TigerBuddy) to process 1,145 PDF papers, extracting structured **Research Cards** (JSON) containing:
    - Title, Authors, Year
    - Entities (Datasets, Metrics, Methods)
    - Relations (e.g., "Proposed Method" -> "Improves")

### Stage 2: Graph Assembly (The Builder)
**Script:** `src/knowledge_graph/graph_builder.py`

Matches were made deterministically:
- **Author Matching**: We used `fuzzywuzzy` to match author names in PDFs (e.g., "C. Kanan") to Faculty Nodes (e.g., "Christopher Kanan") with >85% confidence.
- **Node Creation**:
    - `Faculty` (Blue)
    - `Paper` (Green) - Linked via `[AUTHORED]`
    - `Concept` (Orange) - Linked via `[MENTIONS]`

### Stage 3: Neural Refinement (The Intelligence) 🧠
**Script:** `src/knowledge_graph/graph_refiner.py`

We used `tigerbuddy` (LLM) to upgrade the raw graph:
1.  **Deduplication**: Merged synonymous concepts (e.g., "CNN", "ConvNet", "Convolutional Network" -> Single Node).
2.  **Taxonomy Generation**: The LLM analyzed the top 50 most connected concepts and generated a hierarchical taxonomy, adding `Topic Cluster` nodes (Purple) like "Computer Vision" or "Deep Learning" and linking concepts to them via `[IS_A]` edges.

## 3. Results & Metrics

| Metric | Count |
| :--- | :--- |
| **Total Nodes** | **44,959** |
| **Total Edges** | **46,241** |
| **Faculty Nodes** | ~170 |
| **Paper Nodes** | 1,060 |
| **Concept Nodes** | ~43,000 |

## 4. Key Learnings
1.  **LLM > Regex**: Using an LLM for "Neural Refinement" was critical. The raw graph was too noisy (too many variations of the same concept). The LLM cleaned this up effectively.
2.  **Hybrid is Best**: Neither the Site Graph nor the Research Graph alone was sufficient. Merging them solidified the link between *People* and *Ideas*.
3.  **Visualization Matters**: The PyVis visualization proved that the graph is dense and highly interconnected, validating our hypothesis that RIT's research is collaborative.

## 5. Next Steps
- **Integration**: The Chatbot needs to be updated to query `tiger_brain_refined.gml` for complex questions.
- **Continuous Learning**: implementing a pipeline to add new papers automatically.
