# 04 - Configuration

**Last Updated:** February 9, 2026  
**Purpose:** Complete configuration reference for all system parameters

---

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Environment Variables](#environment-variables)
3. [Config File Reference](#config-file-reference)
4. [Ollama Configuration](#ollama-configuration)
5. [Prompt Templates](#prompt-templates)
6. [Performance Tuning](#performance-tuning)

---

## Configuration Overview

TigerBrain uses a multi-layered configuration system:

1. **Environment Variables** (`.env`) - Secrets and deployment settings
2. **Config Module** (`src/utils/config.py`) - Application defaults  
3. **Ollama Modelfile** - LLM system prompts
4. **Prompt Files** (`data/prompts/*.md`) - Persona templates

---

## Environment Variables

### `.env` File Template

```bash
# TigerBrain Configuration
GEMINI_API_KEY=your_api_key_here
OLLAMA_HOST=http://localhost:11434
CRAWL_DELAY=1.0
MAX_PAGES=100
EMBEDDING_MODEL=all-MiniLM-L6-v2
LOG_LEVEL=INFO
```

### Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | None | Google Gemini API key (optional) |
| `OLLAMA_HOST` | `localhost:11434` | Ollama server address |
| `CRAWL_DELAY` | `1.0` | Seconds between requests |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |

---

## Config File Reference

**Location:** `src/utils/config.py`

**Key Constants:**
```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "rit_research"
CRAWL_DELAY = 1.0
```

---

## Ollama Configuration

### Custom Model Creation

**Modelfile:**
```dockerfile
FROM qwen2.5:latest

SYSTEM """
You are TigerResearchBuddy...
(See data/prompts/role.md)
"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
```

**Build Command:**
```bash
ollama create tigerbuddy -f Modelfile.tigerbuddy
```

---

## Prompt Templates

### Location: `data/prompts/`

**role.md** - Default "Tiger" persona  
**analyzer.md** - Data-focused analyst  
**critique.md** - Critical reviewer
**chain_of_density.md** - Recursive density prompt for CoD

**Example** (role.md):
```markdown
# Role: TigerResearchBuddy

## Identity
You are an AI Research Assistant for RIT Golisano College.

## Constraints
1. NO HALLUCINATIONS
2. CITE SOURCES
3. PROFESSIONAL

## Response Format
1. Direct Answer
2. Key Details
3. Next Steps
```

---

## Performance Tuning

### Vector Search Performance

**Faster (Lower Accuracy):**
```python
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim, fast
```

**Slower (Higher Accuracy):**
```python
EMBEDDING_MODEL = "all-mpnet-base-v2"  # 768-dim, accurate
```

### LLM Inference Speed

**Quantization:**
```bash
ollama pull qwen2.5:7b-q4_0  # 4-bit quantized (2x faster)
```

**Context Window:**
```python
PARAMETER num_ctx 4096  # Smaller = faster
```

---

**Next:** [Data Pipeline →](./05_data_pipeline.md)
