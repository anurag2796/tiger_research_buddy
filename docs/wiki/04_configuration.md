# 04 - Configuration

**Last Updated:** March 9, 2026  
**Purpose:** Complete configuration reference for all system parameters

---

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Environment Variables](#environment-variables)
3. [CrawlConfig — Pipeline Modes](#crawlconfig--pipeline-modes)
4. [Ollama Configuration](#ollama-configuration)
5. [Prompt Templates](#prompt-templates)
6. [PDF Pipeline Options](#pdf-pipeline-options)
7. [Performance Tuning](#performance-tuning)

---

## Configuration Overview

TigerBrain uses a multi-layered configuration system:

1. **Environment Variables** (`.env`) — secrets and deployment settings.
2. **Config Module** (`src/utils/config.py`) — application defaults and pipeline mode config.
3. **Ollama Modelfile** — LLM system prompt baked into the model.
4. **Prompt Files** (`data/prompts/*.md`) — switchable persona templates.
5. **CLI Arguments** (`run_pipeline.py`) — per-run overrides for pipeline, PDF engine, etc.

---

## Environment Variables

### `.env` File Template (copy from `.env.example`)

```bash
# TigerBrain Configuration
GEMINI_API_KEY=your_api_key_here        # Optional — only if using Gemini as LLM fallback
OLLAMA_HOST=http://localhost:11434       # Ollama server address
CRAWL_DELAY=1.0                         # Seconds between HTTP requests
MAX_PAGES=100                           # Cap on pages crawled per run
EMBEDDING_MODEL=all-MiniLM-L6-v2       # SentenceTransformer model name
LOG_LEVEL=INFO                          # DEBUG | INFO | WARNING | ERROR
```

### Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | None | Google Gemini key (optional cloud fallback) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `CRAWL_DELAY` | `1.0` | Polite delay between crawl requests (seconds) |
| `MAX_PAGES` | `100` | Hard cap on pages visited per crawl session |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer for ChromaDB embeddings |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## CrawlConfig — Pipeline Modes

**Location:** `src/utils/config.py`

The system uses a `CrawlConfig` dataclass to manage two operating environments.

### Modes

| Mode | Profiles | Data Dir | Use Case |
|------|----------|----------|----------|
| `restricted` | ~10 | `data/restricted/` | Dev, testing, rapid iteration |
| `full` | All CS faculty | `data/` | Production runs |

### CrawlConfig Fields

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CrawlConfig:
    MODE: str                        # "restricted" or "full"
    START_URLS: list[str]            # Entry points for SmartCrawler
    MAX_PROFILES: int                # Max faculty profiles to scrape
    PAPER_LIMIT_PER_FACULTY: int     # PDFs to download per professor
    CONCURRENCY: int                 # Async worker count
    OUTPUT_FILE: Path                # Path to rit_data.json
    PDF_DIR: Path                    # Path to downloaded PDFs
```

### Usage

```python
from src.utils.config import RESTRICTED_CONFIG, FULL_CONFIG

# In run_pipeline.py (automatic, based on --mode flag)
config = FULL_CONFIG if args.mode == "full" else RESTRICTED_CONFIG

# Manual
from src.utils.config import get_config
config = get_config("restricted")
```

### Resetting Restricted Mode Data

```bash
rm -rf data/restricted/
rm -f data/crawler_checkpoint_restricted.json
python run_pipeline.py --mode restricted
```

---

## Ollama Configuration

### Custom Model Creation

**Modelfile:** `Modelfile.tigerbuddy`
```dockerfile
FROM qwen2.5:latest

SYSTEM """
You are TigerResearchBuddy, an AI Research Advisor for RIT's Golisano College...
(See data/prompts/role.md for full system prompt)
"""

PARAMETER temperature 0.3
PARAMETER top_p       0.9
PARAMETER num_ctx     8192
```

> **Why `num_ctx 8192`?** Standard 2k context truncates schema instructions in TigerCard 2.0 prompts, leading to hallucinated or incomplete JSON output. 8k is required for reliable schema adherence.

**Build & Verify:**
```bash
ollama create tigerbuddy -f Modelfile.tigerbuddy
ollama list               # Verify model is available
ollama run tigerbuddy "Say hello"   # Quick smoke test
```

---

## Prompt Templates (V2 Architecture)

**Location:** `data/prompts/`

In version 2.0, all prompts have been refactored under the "Strict Grounding" architecture to prevent LLM hallucination and ensure output verifiability. Each file includes an Identity, Absolute Laws, and a mandatory Socratic/Formatted Output structure.

| File | Persona | Structural Constraints |
|------|---------|-----------------------|
| `role.md` | Tiger (default) | Strict grounding to `<Context>`. Forces explicit inline citations. |
| `skills.md` | Few-Shot Examples | Uses `[Thought Process]` blocks to evaluate metrics before outputting answers. |
| `analyzer.md` | Quantitative Eval | Forces outputs into markdown tables. Never invents missing numerical data. |
| `critique.md` | Devil's Advocate | Forces the "Sandwich" Protocol (Validate, Tear-Down, Path Forward). |
| `chain_of_density.md` | CoD Synthesizer | Strict JSON output only. Forces extraction of specific metrics or entities. |

**Switching Personas at Runtime (web app sidebar):**
```python
# Via OllamaClient
client.set_persona("critique")   # tiger | analyzer | critique
```

**Persona loading is cached** — switching doesn't reload the entire model.

**Architectural Example (`role.md` snippet):**
```markdown
# Role: TigerResearchBuddy 🐅 (System Prompt)

## THE THREE ABSOLUTE LAWS 🛡️
1. **STRICT GROUNDING:** You MUST NOT answer questions using your internal baseline knowledge. Every claim must trace to the `<Context>`.
2. **EXPLICIT CITATION:** When citing a professor's research, use explicit inline references.
3. **SCOPE BOUNDARIES:** Firmly decline requests to write homework or answer non-RIT queries.

## Response Architecture 📝
1. Direct Answer
2. Evidence/Details (Bullet Points)
3. Accessibility (Feynman Technique)
4. Actionable Next Step
```

---

## PDF Pipeline Options

### Engine Selection (`--engine`)

| Engine | Description | Speed | Quality |
|--------|-------------|-------|---------|
| `apple_fast` **(default)** | Digital gate → Surya MPS → GMFT | **245× faster** for digital PDFs | High |
| `marker` | Full Marker-PDF VLM pipeline | ~4–7s per page | Highest (for scanned docs) |

```bash
python run_pipeline.py --engine apple_fast   # Default (always try this first)
python run_pipeline.py --engine marker        # Legacy, use only for scanned docs
```

### PDF Rendering Backend (`--pdf-backend`)

| Backend | License | Use Case |
|---------|---------|----------|
| `pymupdf` **(default)** | AGPL | Best performance and rendering fidelity |
| `pypdfium2` | Apache 2.0 | Use when AGPL compliance is required |

### Table Extraction Strategy (`--tables`)

| Strategy | Description |
|----------|-------------|
| `auto` **(default)** | Heuristic scan → Surya layout → GMFT extraction |
| `force` | Force table extraction on every page (slower) |
| `off` | Skip table extraction entirely (fastest) |

### Performance Variants

```bash
# Fastest — completely skip tables (pure text extraction)
python run_pipeline.py --engine apple_fast --tables off

# Balanced (default)
python run_pipeline.py --engine apple_fast --tables auto

# Highest quality for problem PDFs
python run_pipeline.py --engine marker

# AGPL-free setup
python run_pipeline.py --pdf-backend pypdfium2
```

**Render DPI:** `--render-dpi 96` (default). Lower = faster, higher = better OCR accuracy.  
**Min digital chars:** `min_digital_chars=50` — threshold to skip OCR when digital text is present.

---

## Performance Tuning

### Vector Search

| Setting | Config | Effect |
|---------|--------|--------|
| Faster (lower accuracy) | `EMBEDDING_MODEL = "all-MiniLM-L6-v2"` | 384-dim, 50ms/query |
| Slower (higher accuracy) | `EMBEDDING_MODEL = "all-mpnet-base-v2"` | 768-dim, 150ms/query |
| Future best option | `nomic-embed-text-v1.5` via Ollama | 8192 context, Matryoshka embeds |

### LLM Inference Speed

```bash
# Use quantized model — 2–3× faster, ~10% quality tradeoff
ollama pull qwen2.5:7b-q4_0
```

Reduce context window for faster responses:
```dockerfile
# In Modelfile — smaller context = faster inference
PARAMETER num_ctx 4096   # Down from 8192 (watch for schema failures)
```

### Crawl Speed vs. Politeness

```python
# config.py
CRAWL_DELAY = 0.5    # Faster but risks rate-limiting
CRAWL_DELAY = 2.0    # Safer for aggressive server-side limits
```

---

**Next:** [Data Pipeline →](./05_data_pipeline.md)
