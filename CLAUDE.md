# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python (Core Backend & Data Pipeline)
- **Run Interactive Chat (Gemini)**: `python main.py chat`
- **Run Offline Chat (Ollama)**: `python main.py chat-offline`
- **Run FastAPI Backend**: `uvicorn api:app --reload`
- **Run Web Interface (Streamlit)**: `streamlit run web_app.py`
- **Run TigerStack 2.0 UI**: `streamlit run src/ui/app.py`
- **Data Ingestion**:
  - Crawl RIT data: `python main.py crawl`
  - Load data to vector DB: `python main.py load`
  - Clear database: `python main.py clear`
  - Full pipeline with distillation: `python main.py scrape-all`

### Testing
- **Run all tests**: `pytest` (config in `pytest.ini`, tests in `tests/`)
- **Run a single test file**: `pytest tests/unit/test_config.py`
- **Run by marker**: `pytest -m unit` or `pytest -m integration`
- **Legacy ad-hoc tests** (not pytest): `python tests/test_persona.py`, `python tests/test_matcher.py`

### Frontend (Next.js)
- **Start Dev Server**: `npm run dev` (in `frontend/`)
- **Build App**: `npm run build` (in `frontend/`)
- **Lint Code**: `npm run lint` (in `frontend/`)

### Setup
- **Install Python Dependencies**: `pip install -r requirements.txt`
- **Install Frontend Dependencies**: `cd frontend && npm install`
- **Initialize Local LLM**: `ollama pull tigerbuddy`
- **Jetson Orin setup**: `bash ORIN_SETUP.sh`

## Architecture

TigerResearchBuddy uses a **hybrid RAG** architecture combining ChromaDB vector search with BM25 keyword search (Reciprocal Rank Fusion), plus a NetworkX knowledge graph for relationship traversal.

### Entry Points
- `main.py` — CLI (click-based) for chat and data pipeline commands
- `api.py` — FastAPI backend serving the Next.js frontend; initializes all services in a lifespan context manager
- `web_app.py` — Streamlit interface (legacy / demo)
- `src/ui/app.py` — TigerStack 2.0 Streamlit interface

### Data Pipeline (offline, run once)
1. **Crawl** (`src/crawlers/`): `rit_crawler.py` scrapes faculty profiles; `smart_crawler.py` uses LLM-powered extraction; `paper_downloader.py` fetches PDFs from ArXiv/Semantic Scholar into `data/papers/`
2. **Distill** (`src/processors/pdf_distiller.py`): VLM-based extraction producing structured "Research Cards" (Level 3) from PDFs
3. **Knowledge Graph** (`src/knowledge_graph/`): `graph_builder.py` builds a NetworkX graph (Faculty ↔ Papers ↔ Concepts); `entity_resolver.py` deduplicates nodes; serialized to `data/tiger_brain.json`
4. **Index** (`src/database/`): `vector_store.py` wraps ChromaDB; `database.py` is the SQLAlchemy layer; embeddings use `nomic-ai/nomic-embed-text-v1.5`

### Runtime Query Path
1. `src/retrieval/hybrid_retriever.py` — fuses ChromaDB vector results + BM25 via RRF, then optionally re-ranks with `reranker.py` (CrossEncoder)
2. `src/generation/synthesizer.py` — builds the final prompt and calls the LLM (Ollama or Gemini)
3. `src/memory/session_store.py` — sliding-window conversation memory (window size is hardware-aware)
4. `src/collaboration/matcher.py` + `src/analysis/impact_analyzer.py` — collaboration hub features

### Hardware Abstraction
`src/utils/hardware.py` is the **single source of truth** for all hardware-aware decisions. It builds `HW_PROFILE` (a frozen dataclass) at import time by probing PyTorch/CUDA/MPS availability. All concurrency limits, context window sizes, embedding devices, and PDF engine choices come from `HW_PROFILE`. Override via environment variables (e.g. `LLM_CONTEXT_WINDOW`, `EMBEDDING_DEVICE`, `PDF_ENGINE`). Never hardcode device flags or resource limits elsewhere.

### Configuration
`src/utils/config.py` imports `HW_PROFILE` and exposes:
- `RESTRICTED_CONFIG` / `FULL_CONFIG` — two `CrawlConfig` presets (10 vs 1000 faculty)
- `LLMConfig` — model names and generation options, hardware-aware context window
- `GEMINI_API_KEY` — read from `.env`; required for Gemini mode

### Key Design Decisions
- **Dual storage**: ChromaDB for semantic search, BM25 (rank_bm25) for keyword search; fused by RRF in `HybridRetriever`
- **Dual LLM strategy**: `LLMConfig.CHAT_MODEL` (`llama3.1:8b`) for interactive use; `PIPELINE_MODEL` for offline distillation
- **`libs/` directory**: Local `.so` files for Jetson/CUDA library dependencies (e.g. `libcusparseLt.so.0`); loaded at `hardware.py` import time via `ctypes`
- Only `computing` college is crawled by default; other colleges are commented out in `COLLEGE_URLS`
