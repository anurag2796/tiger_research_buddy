# TigerResearchBuddy — Jetson Orin Deployment & Refactor Prompt
# ═══════════════════════════════════════════════════════════════
# Copy this file to the Jetson and feed it to Claude Code:
#   cat CLAUDE_CODE_PROMPT.md | claude
# Or paste it as the initial prompt in an interactive session.

---

## System Role

You are a Senior Python Systems Engineer specializing in edge-AI deployment on NVIDIA Jetson platforms. You are working on **TigerResearchBuddy**, an AI-powered research discovery platform for RIT (Rochester Institute of Technology). The codebase has been pulled to this Jetson Orin device and needs to be made production-ready for a demo in 5 days.

Your working model is **Gemma 4:26b** running via Ollama on this Jetson. The project itself also uses Ollama for LLM inference.

## 1. HARDWARE CONTEXT

- **Device**: NVIDIA Jetson Orin (check `cat /etc/nv_tegra_release` and `free -h` for exact variant)
- **Memory**: Unified LPDDR5 (shared CPU/GPU). Check available with `free -h`
- **GPU**: NVIDIA Ampere (CUDA available via JetPack 6+)
- **Ollama**: Already installed or install with `curl -fsSL https://ollama.com/install.sh | sh`
- **Python**: 3.10+ required

## 2. CRITICAL FIRST STEPS (Do these before anything else)

### 2A. Environment Setup
```bash
# Copy the Jetson-optimized env
cp .env.jetson .env

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (some may need Jetson-specific wheels)
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# If sentence-transformers fails on ARM64, install PyTorch for Jetson first:
# See: https://forums.developer.nvidia.com/t/pytorch-for-jetson/
# Then: pip install sentence-transformers
```

### 2B. Ollama Model Selection
The project references these models in `src/utils/config.py` → `LLMConfig`:
- `llama3.2:latest` (CHAT_MODEL — interactive)
- `tigerbuddy:latest` (PIPELINE_MODEL — offline processing)

**Neither may exist on this Jetson.** Run:
```bash
ollama list
```

Based on available unified memory (check with `free -h`), pull the BEST model that fits:

| Jetson Variant | Available RAM | Recommended Model | Pull Command |
|---|---|---|---|
| AGX Orin 64GB | ~55GB usable | `llama3.1:8b` or `gemma2:9b` | `ollama pull llama3.1:8b` |
| AGX Orin 32GB | ~25GB usable | `llama3.2:3b` or `phi4-mini:3.8b` | `ollama pull llama3.2:3b` |
| Orin NX 16GB | ~12GB usable | `llama3.2:1b` or `phi4-mini:3.8b-q4_0` | `ollama pull llama3.2:1b` |
| Orin Nano 8GB | ~5GB usable | `llama3.2:1b` or `tinyllama:1.1b` | `ollama pull tinyllama` |

**After pulling, update `src/utils/config.py`:**
```python
class LLMConfig:
    CHAT_MODEL = "<your_pulled_model>"      # e.g. "llama3.2:3b"
    PIPELINE_MODEL = "<your_pulled_model>"  # same model on Jetson (single model strategy)
```

Also verify the embedding model works:
```bash
python3 -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', device='cuda'); print('OK:', m.encode(['test']).shape)"
```
If CUDA embedding fails, set `EMBEDDING_DEVICE=cpu` in `.env`.

### 2C. Verify Hardware Detection
```bash
python3 -m src.utils.hardware
```
This should print a table showing `platform: linux_cuda`, `has_cuda: True`, `embedding_device: cuda`.

## 3. KNOWN BUGS TO FIX

### BUG 1: Conversation Memory Not Connected in RAG Engine (CRITICAL)
**File**: `src/chatbot/rag_engine.py`
**Problem**: `RAGEngine.query()` maintains a local `self.conversation_history: list[dict]` (line 38) but NEVER injects it into the LLM prompt. The `_expand_query()` method (line 172) does a crude pronoun check but the actual conversation turns are never sent to the LLM — the chatbot has NO memory between turns.

Meanwhile, `api.py` uses `MemoryModule` (from `src/memory/session_store.py`) which IS properly connected via the `ResponseSynthesizer.synthesize_async()` `history` parameter. So the **API path works**, but the **CLI `chat` command DOES NOT have memory**.

**Fix**: Refactor `RAGEngine.query()` to accept and inject conversation history. Either:
- (A) Integrate `MemoryModule` into `RAGEngine` (preferred — unifies the memory layer), OR
- (B) Build the message history into the Gemini/Ollama prompt inside `query()`.

Make sure `main.py`'s `chat` command loop passes history through.

### BUG 2: Missing Methods in Synthesizer (FIXED — verify)
**File**: `src/generation/synthesizer.py`
**Problem**: `synthesize_stream_async()` calls `self._format_sources()` and `self._build_context_string()` which were recently added. Verify these exist and work:
```python
python3 -c "from src.generation.synthesizer import ResponseSynthesizer; s = ResponseSynthesizer(); print(hasattr(s, '_format_sources'), hasattr(s, '_build_context_string'))"
```
Expected output: `True True`

### BUG 3: Crawler Not Restricted to CS Department
**File**: `src/crawlers/smart_crawler.py`
**Problem**: The `valid_paths` filter (line 75) only accepts `/computing/`, `/directory/`, `/people/`, `/research/`, `/faculty-staff`. This is too broad — it can crawl engineering, science, business faculty if their profile URLs contain `/directory/` or `/people/`.

**Fix**: Add explicit domain restriction. The crawler should ONLY follow links under `rit.edu/computing/` or whose page content indicates the Golisano College of Computing and Information Sciences. Add an affiliation check in `extract_profile_data()` that rejects profiles where `college` is not "Computing" / "Golisano" / "GCCIS".

### BUG 4: Paper Downloader Not Filtering RIT-Only Papers
**File**: `src/crawlers/paper_downloader_v3.py`
**Problem**: When searching Semantic Scholar, the code checks `has_rit_affiliation` (line 366-378) but NEVER filters on it — all papers are kept regardless. The comment on line 381 says "Compromise: Keep if strong name match" which means non-RIT papers can contaminate the database.

**Fix**: For the demo, add a strict filter: skip papers where `has_rit_affiliation` is False AND the search was not an explicit name search for a known RIT faculty member. This prevents generic "John Smith" matches from adding irrelevant papers.

### BUG 5: `main.py` References Missing Functions
**File**: `main.py` lines 343, 370, 454-455
**Problem**: Imports like `crawl_extended_sources`, `add_extended_to_vectorstore`, `crawl_phd_students`, `add_phd_to_vectorstore`, `crawl_rit` are used in CLI commands but NOT exported from `src/crawlers/__init__.py`. These commands will crash with ImportError.

**Fix**: Either implement these in the crawlers package, or remove the CLI commands that reference them (`crawl-extended`, `crawl-phd`, `full-setup`). For the demo, removing unused CLI commands is safer.

### BUG 6: `smart_crawler.py` Has Duplicate Method Definition
**File**: `src/crawlers/smart_crawler.py` lines 95-101 and 103-168
**Problem**: `extract_profile_data` is defined twice — first as a placeholder `pass` (line 95), then as the real implementation (line 103). The second definition shadows the first, so it works, but this is a code smell and confusing.

**Fix**: Remove the first placeholder definition (lines 95-101).

## 4. CODE REFACTORING PLAN

The codebase is a flat monolith. Refactor into clean layers:

### Target Package Structure
```
src/
├── __init__.py
├── config/                    # NEW: Configuration layer
│   ├── __init__.py
│   ├── settings.py           # MOVE from src/utils/config.py
│   └── hardware.py           # MOVE from src/utils/hardware.py
├── models/                    # NEW: Data models layer
│   ├── __init__.py
│   ├── faculty.py            # Pydantic models for Faculty, Paper, etc.
│   ├── idea.py               # MOVE from src/database/models.py
│   └── chat.py               # ChatRequest, ChatResponse models
├── data/                      # Renamed from crawlers + database
│   ├── __init__.py
│   ├── crawlers/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract BaseCrawler class
│   │   ├── smart_crawler.py
│   │   ├── paper_downloader.py
│   │   ├── scholar_crawler.py
│   │   └── vision_crawler.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── vector_store.py   # ChromaDB wrapper
│   │   └── graph_store.py    # KuzuDB + NetworkX
│   └── processors/
│       ├── __init__.py
│       ├── pdf_distiller.py
│       └── document_processor.py
├── retrieval/                 # Retrieval layer (keep as-is but clean)
│   ├── __init__.py
│   ├── hybrid_retriever.py
│   ├── reranker.py
│   └── entity_extraction.py
├── chat/                      # Renamed from chatbot + generation + memory
│   ├── __init__.py
│   ├── engine.py             # Unified RAG engine (merge rag_engine.py + query_engine.py)
│   ├── memory.py             # MOVE from src/memory/session_store.py
│   ├── synthesizer.py        # MOVE from src/generation/synthesizer.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract BaseLLMClient
│   │   ├── ollama_client.py
│   │   └── gemini_client.py
│   └── postprocessor.py
├── analysis/                  # Keep as-is
│   ├── __init__.py
│   └── impact_analyzer.py
├── collaboration/             # Keep as-is
│   ├── __init__.py
│   └── matcher.py
├── knowledge_graph/           # Keep as-is
│   └── ...
├── ui/                        # Keep as-is
│   └── ...
└── utils/                     # Slim down — only truly generic utilities
    ├── __init__.py
    ├── timer.py
    ├── db_logger.py
    ├── dedup.py
    ├── json_utils.py
    └── tag_generator.py
```

**IMPORTANT Refactoring Rules:**
1. **Move files one at a time**, updating ALL imports across the codebase after each move.
2. **Keep backward-compatibility aliases** in the old locations for one commit, then remove.
3. **Run `python -c "import src"` after every move** to verify no import crashes.
4. **Do NOT refactor and fix bugs in the same commit.** Fix bugs first (Section 3), then refactor.

## 5. COMPREHENSIVE TEST SUITE

Create the following test structure:

```
tests/
├── conftest.py                # Shared fixtures (mock Ollama, mock ChromaDB, etc.)
├── unit/
│   ├── test_config.py         # Test hardware detection, config loading
│   ├── test_memory.py         # Test MemoryModule sliding window, session isolation
│   ├── test_vector_store.py   # Test VectorStore CRUD, search, embedding
│   ├── test_hybrid_retriever.py  # Test RRF fusion, BM25, vector search
│   ├── test_synthesizer.py    # Test _format_context, _format_sources, _build_context_string
│   ├── test_ollama_client.py  # Test persona loading, model fallback, semaphore
│   ├── test_query_engine.py   # Test keyword extraction, ego-graph traversal
│   ├── test_crawler.py        # Test link extraction, profile filtering, RIT-only
│   ├── test_paper_downloader.py  # Test author matching, affiliation filtering
│   ├── test_postprocessor.py  # Test response cleaning
│   └── test_json_utils.py     # Test extract_json, extract_and_validate
├── integration/
│   ├── test_rag_pipeline.py   # End-to-end: query → retrieval → synthesis
│   ├── test_api_endpoints.py  # FastAPI TestClient for /api/chat, /api/idea, etc.
│   ├── test_memory_api.py     # Test session memory persists across API calls
│   └── test_crawler_pipeline.py  # Test crawl → index → search roundtrip
└── fixtures/
    ├── sample_faculty.json    # 3-5 fake faculty profiles
    ├── sample_papers.json     # 3-5 fake paper metadata
    └── sample_rit_data.json   # Minimal rit_data structure for testing
```

### Key Test Requirements

**conftest.py** should provide:
```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.fixture
def mock_ollama():
    """Mock Ollama client that returns deterministic responses."""
    client = MagicMock()
    client._initialized = True
    client.model = "test-model"
    client.generate.return_value = "Test response about RIT research."
    client.generate_async = AsyncMock(return_value="Test async response.")
    client._load_persona_prompt.return_value = "You are a test assistant."
    return client

@pytest.fixture
def mock_vector_store():
    """Mock VectorStore with sample documents."""
    store = MagicMock()
    store._initialized = True
    store.search.return_value = [
        {
            "id": "prof_test_professor",
            "content": "Professor: Test Professor\nDepartment: Computer Science\nResearch: Machine Learning",
            "metadata": {"doc_type": "professor", "name": "Test Professor", "email": "test@rit.edu"},
            "distance": 0.1
        }
    ]
    store.get_stats.return_value = {"total_documents": 100, "collection_name": "test"}
    return store

@pytest.fixture
def sample_faculty():
    """Sample faculty data for testing."""
    return [
        {
            "name": "Christopher Kanan",
            "title": "Professor",
            "department": "Computer Science",
            "college": "Golisano College of Computing",
            "email": "christopher.kanan@rit.edu",
            "research_interests": ["Computer Vision", "Deep Learning", "Continual Learning"],
            "bio": "Chris Kanan directs the kLab at RIT..."
        }
    ]
```

**Critical tests to write:**

1. **test_memory.py**: Verify sliding window eviction (maxlen), session isolation, async safety
2. **test_hybrid_retriever.py**: Verify RRF fusion ranks docs appearing in both BM25+vector higher
3. **test_synthesizer.py**: Verify `_format_sources` deduplicates, `_build_context_string` numbers correctly
4. **test_crawler.py**: Verify `extract_links` only returns `/computing/` paths, rejects `/engineering/`
5. **test_paper_downloader.py**: Verify `_is_author_match` handles "J. Smith" vs "John Smith" correctly
6. **test_api_endpoints.py**: Use `httpx.AsyncClient` with FastAPI TestClient, verify session_id roundtrip

Run tests with:
```bash
python -m pytest tests/ -v --tb=short -x
```

## 6. JETSON-SPECIFIC OPTIMIZATIONS

### 6A. Reduce Memory Footprint
- The `sentence-transformers` model `nomic-ai/nomic-embed-text-v1.5` is ~280MB. It MUST be loaded only ONCE (it currently is via `_get_embedding_function()` singleton). Verify this.
- ChromaDB PersistentClient should use the local `data/chroma` directory. Verify it's not trying to load the full 70MB SQLite `tiger_research.db` AND ChromaDB simultaneously.

### 6B. CUDA Memory Management
Add to `api.py` startup:
```python
import torch
if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(0.7)  # Reserve 30% for OS/Ollama
```

### 6C. Ollama Configuration
Create `/etc/systemd/system/ollama.service.d/override.conf` (if using systemd):
```ini
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
```

### 6D. Reduce BM25 Index Size
Optionally limit the BM25 corpus to the top 500 most relevant documents if memory is tight.

## 7. DEMO CHECKLIST

Before the demo, verify these work end-to-end:

- [ ] `python main.py chat-offline` — Interactive CLI chat works with conversation memory
- [ ] `uvicorn api:app --host 0.0.0.0 --port 8000` — API starts, health check passes
- [ ] `curl -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{"query": "Who works on computer vision?", "persona": "tiger"}'` — Returns valid response with sources
- [ ] Session memory: Send two queries with same session_id, second references "he/she" — response maintains context
- [ ] `cd frontend && npm run dev` — Next.js UI starts and connects to API
- [ ] Graph visualization at `/api/graph` returns data
- [ ] `python -m pytest tests/ -v` — All tests pass

## 8. EXECUTION ORDER

Follow this exact sequence:

1. **Setup**: Copy `.env.jetson` → `.env`, install deps, pull Ollama model, verify hardware detection
2. **Bug fixes** (Section 3): Fix bugs 1, 3, 4, 5, 6 — commit after each fix
3. **Tests** (Section 5): Write `conftest.py` and test files — verify all pass
4. **Refactor** (Section 4): Only if time permits — restructure packages, update imports
5. **Optimize** (Section 6): Apply Jetson memory optimizations
6. **Demo check** (Section 7): Run through full checklist

**Time budget**: Bugs (2h) → Tests (3h) → Refactor (4h) → Optimize (1h) → Demo check (1h)

## 9. CODING STANDARDS

- Use `ruff` for linting: `ruff check src/ --fix`
- Type hints on all public methods
- Docstrings on all classes and public methods (Google style)
- No `print()` in library code — use `logging` or `rich.console`
- All new files MUST have a module-level docstring
- Commit messages: `fix:`, `feat:`, `test:`, `refactor:`, `docs:` prefixes
