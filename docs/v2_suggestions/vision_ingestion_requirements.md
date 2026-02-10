# Vision-First Ingestion: Requirements & Tool Selection

**Date:** February 9, 2026
**Status:** Phase 4 Planning

## Objective
Replace `PyMuPDF` (heuristic text extraction) with a Visual Language Model (VLM) or Vision-based layout parser to correctly handle:
1.  **2-Column Layouts:** Standard in academic papers (e.g., IEEE, ACM).
2.  **Tables & Charts:** Capturing structured data usually lost in text extraction.
3.  **Formulas:** Converting LaTeX math correctly.

## Tool Comparison: Marker vs. MinerU (on Mac M-series)

| Feature | Marker (`marker-pdf`) | MinerU (`magic-pdf`) |
| :--- | :--- | :--- |
| **Primary Focus** | RAG, LLM context, Markdown conversion | Pre-training data, High-fidelity Layout |
| **Mac M-series** | ✅ Supported (MPS/CPU) | ✅ Supported (MPS/CPU) |
| **Output** | Markdown (clean), JSON, Images | Markdown, JSON, HTML (Tables) |
| **Table Handling** | Good (Markdown) | Excellent (HTML) |
| **OCR Engine** | Tesseract / Surya (Custom) | PaddleOCR / Custom |
| **System Req** | Py 3.10-3.12, ~4GB RAM | Py 3.10+, 8GB+ RAM, 3GB VRAM |
| **Installation** | `pip install marker-pdf` | Complex (requires specialized libs) |
| **Licensing** | Commercial restrictions (OK for personal) | Apache 2.0 |

## Selected Tool: Marker (`marker-pdf`) 🏆

**Rationale:**
1.  **RAG Optimization:** Marker is specifically capable of cleaning artifacts (headers/footers) which is our #1 pain point.
2.  **Ease of Use:** "Pip installable" usually implies easier integration into our existing `src` codebase.
3.  **Performance:** Lighter weight than MinerU, suitable for running alongside Ollama + LanceDB on a single Mac.

## Implementation Plan (Prototype)

1.  **Environment:**
     ```bash
     pip install marker-pdf
     ```
2.  **Prototype Script** (`src/crawlers/vision_crawler.py`):
    - Input: PDF Path
    - Operation: Convert to Markdown using Marker
    - Output: Save `.md` file alongside PDF
3.  **Integration:**
    - Update `DeepDistiller` text extraction method:
      ```python
      # Old
      text = pymupdf_extract(pdf)
      
      # New
      text = marker_extract(pdf)
      ```

## Fallback Plan
If Marker fails on specific chart-heavy PDFs, we will investigate **scanned PDF** mode in MinerU or a direct VLM pass using `minicpm-v` (via Ollama) for just those pages.
