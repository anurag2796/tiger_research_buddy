# 🐅 TigerBrain: Complete System Documentation

**Version:** 2.2.0 (Fast-by-Default)  
**Last Updated:** February 20, 2026  
**Status:** Active Development  

---

## 📋 Documentation Index

This is the master documentation hub for the TigerBrain system. Documentation is organized into focused modules for deep technical understanding.

### 🏗️ Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| **[01 - Architecture](./01_architecture.md)** | System architecture, design decisions, and technology stack | Architects, Senior Devs |
| **[02 - Code Reference](./02_code_reference.md)** | Module-by-module code walkthrough with examples | Developers |
| **[03 - API Reference](./03_api_reference.md)** | Complete API documentation for all public interfaces | Integration Developers |
| **[04 - Configuration](./04_configuration.md)** | All configuration parameters, environment variables, and tuning | DevOps, System Admins |
| **[05 - Data Pipeline](./05_data_pipeline.md)** | Deep dive into crawling, distillation, and graph construction | Data Engineers |
| **[06 - Deployment](./06_deployment.md)** | Production deployment guide with Docker, monitoring, and scaling | DevOps Engineers |
| **[07 - Troubleshooting](./07_troubleshooting.md)** | Common issues, debugging techniques, and performance optimization | Support, Developers |
| **[08 - Challenges](./08_current_challenges.md)** | Current technical limitations and known issues | Architects, Developers |
| **[09 - Evaluation](./09_evaluation.md)** | Response evaluation framework, 100-query test dataset, scoring templates, and testing workflows | QA, Developers |

---

## 🎯 Quick Navigation

### For New Developers
1. Start with [Architecture](./01_architecture.md) to understand the system
2. Read [Code Reference](./02_code_reference.md) for implementation details
3. Set up using [Deployment](./06_deployment.md)

### For System Administrators
1. Review [Configuration](./04_configuration.md) for tuning parameters
2. Implement [Deployment](./06_deployment.md) procedures
3. Setup monitoring from [Troubleshooting](./07_troubleshooting.md)

### For Integration Partners
1. Read [API Reference](./03_api_reference.md)
2. Review [Configuration](./04_configuration.md) for endpoints
3. Check [Troubleshooting](./07_troubleshooting.md) for common issues

---

## 🔑 Key Concepts

### The TigerStack
TigerBrain uses a hybrid RAG architecture combining:
- **Knowledge Graph** (NetworkX) — Structured faculty/paper/concept relationships
- **Vector Store** (ChromaDB) — Semantic similarity search (BM25 keyword search layered on top)
- **Local LLM** (Ollama / tigerbuddy) — Privacy-preserving, zero-cost inference

### Core Workflows

**Data Ingestion:**
```
SmartCrawler → ScholarCrawler → PaperDownloader → DeepDistiller → GraphBuilder → VectorStore
```

**Query Processing:**
```
User Query → HybridRetriever (Vector + BM25 / Graph) → ResponseSynthesizer → Answer
```

**One-Command Pipeline:**
```bash
python run_pipeline.py --mode restricted    # Dev/test (~10 profiles, fast)
python run_pipeline.py --mode full          # Production (all CS faculty, hours)
```

---

## 🚀 Quick Start Guide

```bash
# 1. Clone and setup
git clone <repo>
cd tiger_research_buddy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: add GEMINI_API_KEY if needed, confirm OLLAMA_HOST

# 3. Pull LLM model
ollama pull qwen2.5
ollama create tigerbuddy -f Modelfile.tigerbuddy

# 4. Run pipeline (restricted = fast dev mode)
python run_pipeline.py --mode restricted

# 5. Launch the app
streamlit run web_app.py
```

**Access:** `http://localhost:8501`

### Pipeline Skip Flags
Each stage can be skipped for partial reruns:
```bash
python run_pipeline.py --skip-crawl                              # Skip crawl, use existing data
python run_pipeline.py --skip-crawl --skip-scholar --skip-download  # Resume from distillation
```

---

## 📖 Document Summaries

### 01 - Architecture
Full system design spanning six layers: Presentation, Application, Intelligence, Data, and Ingestion. Covers the TigerStack philosophy, the Hybrid RAG pattern, technology stack decisions (why NetworkX, why ChromaDB, why Ollama), and the v0.1 → v2.2 evolution history.

### 02 - Code Reference
Module-by-module code walkthrough covering every major class and method across `src/`. Key modules: `SmartCrawler`, `VectorStore`, `GraphBuilder`, `HybridRetriever`, `ResponseSynthesizer`, `OllamaClient`.

### 03 - API Reference
Formal public API for all major classes. Parameter specifications, return types, error handling, and usage examples. APIs: `VectorStore`, `HybridRetriever`, `GraphBuilder`, `OllamaClient`, `ResponseSynthesizer`.

### 04 - Configuration
Multi-layered config system: `.env` environment variables, `src/utils/config.py` (CrawlConfig with restricted/full mode), Ollama Modelfile, prompt templates, PDF pipeline engine options (`apple_fast` vs `marker`).

### 05 - Data Pipeline
Six-stage pipeline from raw web crawl to a queryable knowledge graph. Covers SmartCrawler's LLM parsing, DeepDistiller's TigerCard 2.0 schema, entity resolution with canonical IDs, graph assembly steps, and quality assurance.

### 06 - Deployment
Three deployment targets: Local Development, Single-Server Production (systemd service), and Docker/Docker Compose. Includes monitoring, backup scripts, and systemd watchdog configuration.

### 07 - Troubleshooting
Quick diagnostic scripts, common error fixes (Ollama not running, graph not found, port conflicts), performance profiling, data quality debugging (duplicate nodes, vector search irrelevant results), and step-by-step component isolation.

### 08 - Challenges
Active limitations: LLM inference latency (15–45s on unquantized), context window limits (8k ceiling), graph traversal explosion on multi-hop queries, entity resolution ambiguity, and no conversational memory. Hardware specs table and known workarounds.

---

## 📂 Project Structure Reference

```
tiger_research_buddy/
├── run_pipeline.py       # ← Main entry point: 6-stage pipeline runner
├── web_app.py            # ← Streamlit UI
├── main.py               # ← CLI utilities
├── src/
│   ├── crawlers/         # SmartCrawler, ScholarCrawler, PaperDownloader
│   ├── processors/       # DeepDistiller (pdf_distiller.py)
│   ├── database/         # VectorStore (ChromaDB wrapper)
│   ├── knowledge_graph/  # GraphBuilder, EntityResolver
│   ├── retrieval/        # HybridRetriever (Vector + BM25 + RRF)
│   ├── generation/       # ResponseSynthesizer
│   ├── chatbot/          # OllamaClient, GeminiClient
│   └── utils/            # config.py, logging
├── data/
│   ├── publications/     # Downloaded PDFs
│   ├── research_cards/   # Distilled TigerCard 2.0 JSONs
│   ├── prompts/          # role.md, analyzer.md, critique.md
│   └── restricted/       # Dev/test data (isolated from production)
├── docs/
│   ├── wiki/             # ← This documentation
│   └── project_journey.md  # Full narrative history and decision log
├── tests/                # pytest test suite
├── scripts/              # Utility scripts (benchmark, health-check, etc.)
└── experiments/          # Sandbox for new ideas
```

---

## 🤝 Contributing

When contributing to TigerBrain:
1. Read relevant wiki sections first
2. Follow code patterns documented in [Code Reference](./02_code_reference.md)
3. Update wiki docs when adding features or changing behavior
4. Add tests as documented in [Troubleshooting](./07_troubleshooting.md)
5. Document significant decisions in `docs/project_journey.md`

---

**Built with ❤️ at RIT** 🐅  
*Last updated: February 20, 2026*
