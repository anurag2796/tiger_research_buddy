# 07 - Troubleshooting

**Last Updated:** February 22, 2026  
**Purpose:** Common issues, debugging techniques, and step-by-step solutions

---

## Table of Contents

1. [Quick Diagnostic](#quick-diagnostic)
2. [Installation Issues](#installation-issues)
3. [Pipeline Errors](#pipeline-errors)
4. [Runtime Errors (Web App)](#runtime-errors-web-app)
5. [Performance Problems](#performance-problems)
6. [Data Quality Issues](#data-quality-issues)
7. [Debugging Techniques](#debugging-techniques)

---

## Quick Diagnostic

### System Health Check

```bash
# Check all pipeline dependencies
python scripts/health_check.py
```

Expected output:
```
✓ Python version: 3.10.x
✓ Ollama service: Running (tigerbuddy available)
✓ Graph file: Found (data/tiger_brain.json — 45,280 nodes)
✓ Vector DB: Initialized (1,523 documents)
✓ Disk space: 42GB free
```

### Common Quick Fixes

```bash
# Fix 1: Restart Ollama
brew services restart ollama            # macOS
sudo systemctl restart ollama           # Linux

# Fix 2: Wipe and rebuild vector DB
rm -rf data/chroma/
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill

# Fix 3: Rebuild knowledge graph only
python -m src.knowledge_graph.graph_builder

# Fix 4: Wipe restricted mode data for clean slate
rm -rf data/restricted/
rm -f data/crawler_checkpoint_restricted.json
python run_pipeline.py --mode restricted
```

---

## Installation Issues

### `ModuleNotFoundError: No module named 'src'`

**Cause:** Running from wrong directory.  
**Fix:**
```bash
cd /path/to/tiger_research_buddy   # Always run from project root
streamlit run web_app.py           # Not from a subdirectory
```

---

### `ollama: command not found`

**Fix:**
```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh
```

---

### `No models found. Run: ollama pull tigerbuddy`

**Fix:**
```bash
ollama pull qwen2.5                          # Pull base model
ollama create tigerbuddy -f Modelfile.tigerbuddy   # Build custom model
ollama list                                  # Verify available
```

---

### `ChromaDB initialization failed` / Permission error

**Fix:**
```bash
# Option 1: Clear and rebuild
rm -rf data/chroma/
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill

# Option 2: Fix permissions
chmod -R 755 data/chroma/
```

---

### Dependency version conflicts

**Symptom:** `ImportError` on chromadb, sentence-transformers, or streamlit.  
**Fix:** The installed versions supersede `requirements.txt` pins. Upgrade cleanly:
```bash
pip install --upgrade chromadb sentence-transformers streamlit
pip install -e .    # Re-install the project package
```

---

## Pipeline Errors

### Stage 1 (Crawl) fails immediately

**Cause:** Ollama not running, or wrong start URL.  
**Diagnosis:**
```bash
curl http://localhost:11434/api/tags   # Test Ollama is up
```
**Fix:**
```bash
ollama serve &    # Start Ollama
# or: brew services start ollama
```

---

### Stage 1 (Crawl) — `'utf-8' codec can't decode byte` errors on binary files

**Cause:** SmartCrawler fetches all URLs and attempts to decode responses as UTF-8 text. Binary responses (`.docx`, `.doc`, `.zip`, `.jpeg`, `.pptx`) are not UTF-8 decodable.  
**Impact:** Low — these are admin/template documents, not faculty research pages. Faculty profile data is unaffected.  
**Fix:** Check the `Content-Type` header before decoding:
```python
response = requests.get(url)
if 'text/html' not in response.headers.get('Content-Type', ''):
    return  # skip binary files
text = response.content.decode('utf-8', errors='ignore')
```

---

### Stage 2 (Scholar) returns 0 enriched

**Cause A — Thread-safety race condition (confirmed Feb 21 2026):** A shared dict is mutated by one thread while another iterates it → `RuntimeError: dictionary changed size during iteration`. All threads for affected faculty crash and no enrichment is saved.

**Fix A:**
```python
# Wrap shared dict mutations in a lock
import threading
_lock = threading.Lock()

with _lock:
    shared_dict[key] = value
```

**Cause B — Google Scholar rate-limiting or block.**  
**Fix B:** Increase crawl delay and retry:
```bash
# Edit .env or config.py:
CRAWL_DELAY = 3.0   # Up from 1.0
```

---

### Stage 3 (Download) — papers skipped due to author mismatch

**This is expected behavior.** The `_is_author_match()` function now rejects:
- Last-name-only collisions (two different people with the same last name).
- Papers where no author name matches the faculty member's known names.

Check `data/publications/download_summary.json` to see what was skipped and why.

---

### Stage 4 (Distill) — LLM returns invalid JSON

**Cause:** Context window too small for the TigerCard schema.  
**Fix:** Verify Modelfile has `num_ctx 8192`:
```bash
ollama show tigerbuddy --modelfile | grep num_ctx
# Should output: num_ctx 8192
```
If not: rebuild the model from `Modelfile.tigerbuddy`.

---

### Stage 4 (Distill) — `RecursionError: maximum recursion depth exceeded` on PDF read

**Cause:** The PDF parser (`pypdf`/`pdfminer`) uses deep recursion on complex or malformed PDF object trees and hits Python's default limit.  
**Diagnosis:** Look for `Error reading <filename>.pdf: maximum recursion depth exceeded` in DB logs.
```bash
sqlite3 data/tiger_research.db "SELECT COUNT(*) FROM logs WHERE level='ERROR' AND message LIKE '%maximum recursion%';"
```
**Fix:**
```python
import sys
sys.setrecursionlimit(5000)   # Add before PDF extraction loop
```
Or switch to a non-recursive parser:
```bash
pip install pymupdf   # fitz — non-recursive, much faster
```

---

### Stage 4 (Distill) — `'str' object has no attribute 'get_image'`

**Cause:** The vision extraction call receives a raw file-path `str` instead of a `Page` object. All multimodal image annotations are silently skipped.  
**Diagnosis:**
```bash
sqlite3 data/tiger_research.db "SELECT COUNT(*) FROM logs WHERE message LIKE \"%'str' object has no attribute 'get_image'%\";"
```
**Fix:** Locate the call site in `DeepDistiller` that calls the image extractor and ensure you're passing the `page` object (e.g. a `fitz.Page` or `pypdf.PageObject`), not the file path string.

---

### Stage 5 (Index) — `Cannot copy out of meta tensor; no data!`

**Cause:** The embedding model was initialized with `torch.device("meta")` (lazy / shape-only tensor with no actual weights) and then moved with `.to(device)`. PyTorch does not allow data copying from a meta tensor.  
**Symptoms:** Stage crashes in ~2 seconds; vector store is completely empty; RAG retrieval returns nothing.  
**Diagnosis:**
```bash
sqlite3 data/tiger_research.db "SELECT message FROM logs WHERE message LIKE '%meta tensor%' LIMIT 3;"
```
**Fix:**
```python
# WRONG
model = ModelClass()   # initializes on meta device
model = model.to(device)

# CORRECT
model = ModelClass()
model = model.to_empty(device)         # allocate storage without copying
model.load_state_dict(torch.load(weights_path, map_location=device))  # load weights
```

---

### Stage 5 (Index) — ChromaDB duplicate ID error

**Cause:** Re-running index on existing data.  
**Fix:** The pipeline uses `upsert()` by default; this should not happen. If it does:
```bash
rm -rf data/chroma/
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill
```

---

### Stage 6 (Graph) — `data/site_graph.gml not found`

**Cause:** Stage 1 (Crawl) was skipped and there is no existing `site_graph.gml`.  
**Fix:** Run Stage 1 first:
```bash
python run_pipeline.py --mode restricted   # Runs all including crawl
```
Or manually generate from existing data:
```bash
python -m src.crawlers.smart_crawler
```

---

## Runtime Errors (Web App)

### `Graph file not found: data/tiger_brain.json`

**Fix:**
```bash
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill --skip-index
# Runs only Stage 6 (graph builder)
```

---

### `Ollama connection refused (localhost:11434)`

**Diagnosis:**
```bash
ps aux | grep ollama
curl http://localhost:11434/api/tags
```

**Fix:**
```bash
brew services start ollama    # macOS
sudo systemctl start ollama   # Linux
ollama serve &                # Manual
```

---

### `KeyError: 'message'` from Ollama

**Cause:** Stale `ollama` Python library.  
**Fix:**
```bash
pip install --upgrade ollama
python -c "import ollama; print(ollama.__version__)"
```

---

### `NameError: name 'QueryEngine' is not defined` (web app)

**Cause:** Missing import in `web_app.py`.  
**Fix:** Ensure `web_app.py` has at the top:
```python
from src.chatbot.query_engine import QueryEngine
```

---

### Port 8501 already in use

```bash
lsof -ti:8501 | xargs kill -9
streamlit run web_app.py --server.port 8502   # Alternative port
```

---

## Performance Problems

### Slow query responses (>10s)

**Profile the bottleneck:**
```python
import time

start = time.time()
results = retriever.hybrid_search(query)
print(f"Retrieval: {time.time() - start:.2f}s")

start = time.time()
response = synthesizer.synthesize(query, results)
print(f"Synthesis: {time.time() - start:.2f}s")
```

**Common fix — use quantized LLM:**
```bash
ollama pull qwen2.5:7b-q4_0
ollama create tigerbuddy-fast -f Modelfile.fast   # Use q4_0 in Modelfile
```

**Reduce context window for faster synthesis:**
```dockerfile
# Modelfile.fast
PARAMETER num_ctx 4096   # Down from 8192
```

---

### High memory usage (>8GB)

**Causes:**
1. Full-precision model loaded → switch to `q4_0`.
2. Large graph in RAM → prune orphan nodes: `python scripts/prune_graph.py`.
3. Surya models loaded during distillation → normal; will drop after pipeline completes.

---

### Streamlit app freezes

**Cause:** Blocking operation in main thread.  
**Fix:** Wrap all heavy calls in `st.spinner`:
```python
with st.spinner("Searching knowledge graph..."):
    results = retriever.hybrid_search(query)
```
Also ensure `@st.cache_resource` is used for all backend instantiation:
```python
@st.cache_resource
def get_engine():
    return HybridRetriever(...), ResponseSynthesizer()
```

---

## Data Quality Issues

### Faculty bio shows "Not available"

**Diagnosis:**
```bash
cat data/rit_data.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for f in data['faculty']:
    if not f.get('bio'): print(f['name'])
"
```

**Fix:**  
Force a re-crawl for that specific professor:
```bash
python -m src.crawlers.smart_crawler --url "https://www.rit.edu/directory/..."
```
Or update `data/entity_mappings.json` manually and rebuild the graph.

---

### Duplicate faculty nodes in graph

**Diagnosis:**
```bash
python scripts/debug_duplicates.py
```

**Fix:** Update `data/entity_mappings.json`:
```json
{
  "faculty": {
    "c. kanan": "faculty_christopher_kanan",
    "chris kanan": "faculty_christopher_kanan"
  }
}
```
Then rebuild: `python -m src.knowledge_graph.graph_builder`

---

### Vector search returns irrelevant results

**Diagnosis:**
```python
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine

model = SentenceTransformer('all-MiniLM-L6-v2')
e1 = model.encode("computer vision")
e2 = model.encode("machine learning")
print(f"Similarity: {1 - cosine(e1, e2):.3f}")   # Should be ~0.5+
```

**Fix:** Rebuild vector DB with correct embedding model:
```bash
rm -rf data/chroma/
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill
```

---

## Debugging Techniques

### Enable Debug Logging

```python
# At top of any script
import logging
logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
```

### Inspect Knowledge Graph Interactively

```python
import json, networkx as nx

with open("data/tiger_brain.json") as f:
    data = json.load(f)

G = nx.node_link_graph(data)

# Find specific node
node = G.nodes["faculty_christopher_kanan"]
print(node)

# Find neighbors (papers authored by Kanan)
neighbors = list(G.neighbors("faculty_christopher_kanan"))
print(neighbors[:5])

# Graph stats
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
```

### Test Pipeline Components Individually

```bash
# Test vector search
python scripts/test_retrieval.py

# Test crawler on a single URL
python -m src.crawlers.smart_crawler --url "https://www.rit.edu/computing/faculty-staff"

# Test distiller on a single PDF
python -m src.processors.pdf_distiller --pdf "data/publications/some_paper.pdf"

# Benchmark graph queries
python scripts/benchmark_graph.py
```

---

**Next:** [Challenges →](./08_current_challenges.md)  
**End of Documentation**
