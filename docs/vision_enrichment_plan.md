# Vision Enrichment Plan (DeepDistiller + Marker-PDF)

**Objective**: Leverage the new `VisionCrawler` (Marker-PDF) to significantly enrich the existing `research_cards` with high-fidelity structured data that was previously lost or corrupted by `PyMuPDF`.

## 1. Why Update? The Data Quality Gap

The previous `PyMuPDF` extraction had critical limitations that `VisionCrawler` solves.

| Feature | Old (PyMuPDF) | New (VisionCrawler) | Impact on Research Card |
| :--- | :--- | :--- | :--- |
| **Layout** | Linear text stream (often mixes columns/sidebars) | **Layout-aware Markdown** | Context is preserved. LLM doesn't hallucinate relationships across columns. |
| **Tables** | Garbage characters / lost structure | **Markdown Tables** | **Critical**: We can now extract specific **Results** and **Metrics** (e.g., "Accuracy: 95%"). |
| **Math** | Garbled symbols | **LaTeX Formulas** | Core methodology equations are preserved. |
| **Artifacts** | Headers/Footers/Page Numbers included | **Removed** | Cleaner context window for LLM, less noise. |

## 2. Enrichment Strategy

We will update `DeepDistiller` to specifically target the new data types available in the Markdown output.

### A. Prompt Engineering (Update `src/processors/pdf_distiller.py`)
Current prompt asks for general "Outcomes".
We will update it to explicitly ask for:
*   **Quantitative Results**: Extract metrics from Markdown Tables.
*   **Key Equations**: Extract central formulas (if present).

### B. Pilot Run (Validation)
Before processing 1,145 papers (~6 hours), we will run a **Pilot Batch of 20 papers**.
1.  Select 20 diverse papers (dense math, multi-column, tables).
2.  Generate new `_card_v2.json`.
3.  Compare `v1` vs `v2` side-by-side.

### C. Full Batch Execution
If the Pilot confirms better data:
1.  Run full batch (1,145 papers) overnight.
2.  Overwrite existing `research_cards` (or archive old ones to `backup/`).
3.  Re-run `GraphBuilder` to populate `TigerGraph` with new entities (Metrics, Equations).

## 3. Execution Plan

1.  **Refine Prompt**: Modify `DeepDistiller` prompt to leverage Markdown structure.
2.  **Run Pilot**: Process 20 papers.
3.  **Review**: User reviews the difference.
4.  **Go/No-Go**: Decide on full batch.

## 4. Expected Outcome
*   **Richer "Outcomes"**: Instead of "Shown to be better", we get "Achieved 95% (+5% vs SOTA)".
*   **Better "Methodology"**: Includes key equation concepts.
*   **Cleaner "Abstract"**: No more "Page 1" interruptions.
