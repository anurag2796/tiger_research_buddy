# AGENTS.md

Welcome to the TigerResearchBuddy codebase! This document provides core context, architectural guidelines, and technical directives for AI agents working on this project.

## 🧠 The Two-Lobe Architecture

TigerResearchBuddy operates using a "Two-Lobe Brain" architecture:
1. **Semantic Vector Lobe:** Uses ChromaDB (and LanceDB for v2 scale) to store document chunks, papers, and faculty profiles for high-speed dense vector retrieval via `hybrid_retriever.py` and `vector_store.py`.
2. **Knowledge Graph Lobe:** A highly structured NetworkX (and KuzuDB) graph that models relationships between `Faculty`, `Paper`, `Concept`, and `Topic` nodes. It allows traversing interdisciplinary connections (e.g., using Personalized PageRank).

Always consider *both* lobes when implementing or upgrading RAG pipelines, data ingestion, and query reasoning. Modifying one without considering the other risks breaking the RRF (Reciprocal Rank Fusion) logic.

## 🔭 Vision-Language Models (VLMs) & Data Processing

- We utilize deep processing pipelines in `src/processors/pdf_distiller.py` and `src/crawlers/smart_crawler.py`.
- **Target Prompting:** For tables and complex layouts, we isolate bounding boxes and use VLM prompts strictly focused on that data.
- **Entity Resolution:** Never rely purely on string matching. Use `src/knowledge_graph/entity_resolver.py` to compare NetworkX neighbor overlaps when disambiguating entities (e.g., authors).

## 💾 Conversational Memory

- The `src/memory/session_store.py` manages persistent multi-session chat histories.
- It operates using a Sliding Window for short-term active context (configurable by `HW_PROFILE.memory_window`).
- It has an optional LanceDB backend for long-term semantic recall across sessions.

## 🛠️ Hardware Constraints & Profiles

- The app must run on both Jetson Orin (Linux/CUDA) and macOS (MPS/CPU).
- Read `src/utils/hardware.py` and respect `HW_PROFILE`. Do not hardcode cache limits or context window sizes; query `HW_PROFILE` instead.
- For heavy batch processing, enforce PyTorch cache clearing (`torch.cuda.empty_cache()`/`torch.mps.empty_cache()`) and Python garbage collection (`gc.collect()`).

## ⚠️ Pre-Commit & PR Guidelines

- Run all linters and tests (e.g., `PYTHONPATH=. pytest`) before completing any plan or PR.
- Use `tenacity` for external API retries (especially crawlers).
- Ensure all KuzuDB Cypher identifiers are validated.

## 📁 Repository Structure Overview

- `src/chatbot/`: Core RAG loop, LLM clients, and Query expansion.
- `src/crawlers/`: RIT web scraping and Paper downloading (ArXiv, Semantic Scholar).
- `src/knowledge_graph/`: Graph building, entity resolution, and network algorithms.
- `src/retrieval/`: Hybrid fusion of Vector Search and Graph Search.
- `src/collaboration/`: Graph-based faculty recommendation and Idea matching.
- `src/analysis/`: Pydantic-validated LLM analysis (SDG Impact, etc.).

By following these architecture rules, you ensure TigerBrain remains a robust, context-aware academic assistant.
