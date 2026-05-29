# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TigerResearchBuddy is a hybrid RAG (Retrieval-Augmented Generation) research discovery platform for RIT. It crawls faculty profiles and publications, distills PDFs into structured "Research Cards," builds a knowledge graph, and serves queries through a dual retrieval pipeline (vector + BM25 + graph traversal) fused via Reciprocal Rank Fusion (RRF).

## Commands

### Environment Setup

```bash
pip install -r requirements.txt    # Core dependencies
pip install -e ".[dev]"            # Dev tools (pytest, ruff, mypy) from pyproject.toml
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. For local LLM, start Ollama separately.

### Run the Data Pipeline

```bash
python run_pipeline.py                            # Restricted mode (default, ~10 faculty)
python run_pipeline.py --mode full                # Full CS department
python run_pipeline.py --skip-crawl               # Skip stage 1 (crawl already done)
python run_pipeline.py --skip-crawl --skip-scholar --skip-download  # Resume from distill
```

The pipeline has 6 stages: Crawl -> Scholar -> Download -> Distill -> Index -> Graph. Each is independently skippable.

### Run the Dagster Pipeline (Alternative)

```bash
dagster dev -m src.pipeline_v2           # Dagster UI at localhost:3000
dagster job execute -j restricted_pipeline -m src.pipeline_v2   # CLI run
```

### Start the Applications

```bash
streamlit run web_app.py                 # Main Streamlit UI (port 8501)
streamlit run src/ui/app.py              # TigerStack 2.0 alternative UI
python -m uvicorn api:app --reload       # FastAPI backend (for Next.js frontend)
```

### Start the Next.js Frontend

```bash
cd frontend && npm run dev               # Next.js dev server
```

### Run Tests

```bash
pytest                                   # All tests (pytest.ini config: ignores legacy/ scripts)
pytest tests/chatbot/test_persona.py     # Single test file
pytest -m unit                           # Unit tests only
pytest -m integration                    # Integration tests only
pytest -k "keyword"                      # Filter by test name
```

### Lint and Type-Check

```bash
ruff check src/                          # Linting
ruff format src/                         # Formatting
mypy src/                                # Type checking
```

## Architecture

### Dual-Lobe Retrieval Architecture

There are two query engines. The graph-enhanced path is the primary one:

- **`src/chatbot/query_engine.py`** — `GraphEnhancedQueryEngine` (and its `QueryEngine` subclass). The full dual-lobe path. Intent detection is *inline* here (see `get_graph_insights`), not a separate module.
- **`src/chatbot/rag_engine.py`** — `RAGEngine`, a simpler vector-only RAG path with its own `query`/`search_only`/`_expand_query`. Used as a lighter alternative.

The core graph-enhanced query flow (`GraphEnhancedQueryEngine`):

1. **Dual-Level Keyword Extraction** (LLM-driven: high-level themes + low-level entities) -> `extract_dual_keywords` in `query_engine.py`
2. **Dual-Level Search** -> `dual_level_search` orchestrates retrieval and ego-graph traversal (`_traverse_ego_graph`)
3. **Hybrid Retrieval** -> `src/retrieval/hybrid_retriever.py`
   - High-level keywords: ChromaDB vector search + ego-graph traversal
   - Low-level keywords: BM25 exact match
   - Results fused via RRF (only RRF implementation lives in `hybrid_retriever.py`)
4. **Response Synthesis** -> `src/generation/synthesizer.py`
5. **Post-Processing** -> `src/chatbot/response_postprocessor.py`

### Pipeline Stages (Data Ingestion)

The data pipeline is defined in two places:
- **`run_pipeline.py`** — standalone runner with rich CLI output, stage-by-stage execution
- **`src/pipeline_v2/`** — Dagster asset-based pipeline (same stages, orchestrated via Dagster)

Both share the same underlying modules:

| Stage | Module | Output |
|---|---|---|
| Crawl | `src/crawlers/smart_crawler.py` | `data/{mode}/rit_data_{mode}.json` |
| Scholar | `src/crawlers/scholar_crawler.py` | Enriched faculty data in-place |
| Download | `src/crawlers/paper_downloader_v3.py` | `data/{mode}/pdfs/` |
| Distill | `src/processors/pdf_distiller.py` | `data/{mode}/research_cards/` |
| Index | `src/database/vector_store.py` | ChromaDB at `data/{mode}/chroma/` |
| Graph | `src/knowledge_graph/builder.py` | KuzuDB at `data/{mode}/kuzu_db/` |

> Note: `src/knowledge_graph/` contains both `builder.py` (KuzuDB, current) and `graph_builder.py` (older NetworkX builder). Use `builder.py` for the KuzuDB graph; `graph_builder.py` feeds the legacy `tiger_brain.json` consumed by the FastAPI `/api/graph` endpoint.

### Key Config Classes

- `src/utils/config.py` — `CrawlConfig` (mode, concurrency, paper limits), `LLMConfig` (Ollama model selection, context window), embedding model, all path definitions
- Two modes: `restricted` (small subset, fast iteration) and `full` (entire department)
- LLM dual-model strategy: `CHAT_MODEL` (fast, interactive) vs `PIPELINE_MODEL` (large, offline processing)

### Storage Layer

- **Vector Store**: ChromaDB (persistent, local `data/{mode}/chroma/`). Embedding model: `nomic-ai/nomic-embed-text-v1.5`
- **Knowledge Graph**: KuzuDB (embedded graph database at `data/{mode}/kuzu_db/`). The older NetworkX in-memory graph (`tiger_brain.json`) is legacy but still used by the FastAPI `/api/graph` endpoint.
- **Research Cards**: JSON files in `data/{mode}/research_cards/` — structured paper summaries produced by DeepDistiller

### Entry Points

| File | Purpose |
|---|---|
| `run_pipeline.py` | CLI pipeline runner (primary ingestion entry point) |
| `api.py` | FastAPI backend for Next.js frontend (`/api/chat`, `/api/graph`, `/api/idea`) |
| `web_app.py` | Main Streamlit app (standalone, uses Ollama directly) |
| `main.py` | Legacy CLI interface (chat, crawl, load commands) |
| `src/ui/app.py` | Alternative Streamlit UI |

### LLM Dependencies

- **Ollama**: Local inference. Configured models in `src/utils/config.py:LLMConfig`
- **Gemini**: Cloud API for PDF distillation and data cleaning. Key required in `.env`
- **Prompt templates**: `data/prompts/` (analyzer, critique, crawler extraction rules, distiller schema, role, skills)

### Frontend

The `frontend/` directory is a Next.js 16 + React 19 + Tailwind CSS v4 app. It connects to the FastAPI backend via axios. Uses `react-force-graph-2d` for the knowledge graph visualization.

### Important Conventions

- The `data/` directory is `.gitignore`d. Pipeline outputs live there and should not be committed.
- The `legacy/` directory contains v1 code — do not modify, only reference.
- `scripts/` holds one-off debug/eval/migration utilities and a duplicate `run_pipeline.py`; `experiments/` holds benchmark outputs and scratch runs. Both are `--ignore`d by pytest (see `pytest.ini`) and are not part of the importable `src` package — treat them as throwaway, not API.
- The crawler uses a **checkpoint file** (`data/{mode}/crawler_checkpoint_{mode}.json`) for resumable crawling.
- The API (`api.py`) uses a **file lock** (`data/.pipeline.lock`) to prevent concurrent DB access during pipeline rebuilds.
- Currently only CS department is crawled (other colleges commented out in `src/utils/config.py:COLLEGE_URLS`).
