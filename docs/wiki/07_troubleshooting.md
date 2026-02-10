# 07 - Troubleshooting

**Last Updated:** February 9, 2026  
**Purpose:** Common issues, debugging techniques, and solutions

---

## Table of Contents

1. [Quick Diagnostic](#quick-diagnostic)
2. [Installation Issues](#installation-issues)
3. [Runtime Errors](#runtime-errors)
4. [Performance Problems](#performance-problems)
5. [Data Quality Issues](#data-quality-issues)
6. [Integration Problems](#integration-problems)

---

## Quick Diagnostic

### System Health Check

```bash
# Run diagnostic script
python scripts/health_check.py
```

**Expected Output:**
```
✓ Python version: 3.10.8
✓ Ollama service: Running (tigerbuddy available)
✓ Graph file: Found (45,280 nodes)
✓ Vector DB: Initialized (1,523 documents)
✓ Disk space: 42GB free
```

### Common Quick Fixes

```bash
# Fix 1: Restart Ollama
brew services restart ollama

# Fix 2: Clear ChromaDB cache
rm -rf data/chroma/
python scripts/rebuild_vectordb.py

# Fix 3: Rebuild graph
python src/knowledge_graph/graph_builder.py
```

---

## Installation Issues

### Issue: `ModuleNotFoundError: No module named 'src'`

**Cause:** Running from wrong directory

**Solution:**
```bash
# Always run from project root
cd /path/to/tiger_research_buddy
streamlit run src/ui/app.py
```

---

### Issue: `ollama: command not found`

**Cause:** Ollama not installed

**Solution (macOS):**
```bash
brew install ollama
ollama serve
```

**Solution (Linux):**
```bash
curl https://ollama.ai/install.sh | sh
```

---

### Issue: `No models found. Run: ollama pull tigerbuddy`

**Cause:** Model not downloaded

**Solution:**
```bash
# Pull base model
ollama pull qwen2.5

# Create custom model
ollama create tigerbuddy -f Modelfile.tigerbuddy

# Verify
ollama list
```

---

### Issue: `ChromaDB initialization failed`

**Cause:** Corrupted database or permission issues

**Solution:**
```bash
# Option 1: Clear and rebuild
rm -rf data/chroma/
python main.py load

# Option 2: Fix permissions
chmod -R 755 data/chroma/
```

---

## Runtime Errors

### Issue: `Graph file not found: data/tiger_brain.json`

**Cause:** Graph not built

**Solution:**
```bash
# Build graph from scratch
python src/knowledge_graph/graph_builder.py

# Verify
ls -lh data/tiger_brain.json
```

---

### Issue: `Ollama connection refused (localhost:11434)`

**Cause:** Ollama server not running

**Diagnosis:**
```bash
# Check if Ollama is running
ps aux | grep ollama
curl http://localhost:11434/api/tags
```

**Solution:**
```bash
# macOS
brew services start ollama

# Linux (systemd)
sudo systemctl start ollama

# Manual (any OS)
ollama serve &
```

---

### Issue: `KeyError: 'message'` when calling Ollama

**Cause:** Incorrect Ollama library version or API change

**Solution:**
```bash
# Update ollama library
pip install --upgrade ollama

# Check version
python -c "import ollama; print(ollama.__version__)"
```

---

### Issue: `LLM returns empty response`

**Cause:** Context too long or model offline

**Diagnosis:**
```bash
# Test Ollama directly
ollama run tigerbuddy "Say hello"
```

**Solution:**
```bash
# If model missing
ollama pull tigerbuddy

# If context too long (edit config.py)
PARAMETER num_ctx 4096  # Reduce from 8192
```

---

## Performance Problems

### Issue: Slow query responses (>10s)

**Diagnosis:**
```python
# Add timing logs
import time

start = time.time()
results = retriever.retrieve(query)
print(f"Retrieval: {time.time() - start:.2f}s")

start = time.time()
response = synthesizer.synthesize(query, results)
print(f"Synthesis: {time.time() - start:.2f}s")
```

**Common Bottleneck: LLM Inference (70% of time)**

**Solutions:**
```bash
# Use quantized model (2x faster)
ollama pull qwen2.5:7b-q4_0
ollama create tigerbuddy-fast -f Modelfile.fast

# Reduce context window
# Edit Modelfile: PARAMETER num_ctx 4096

# Disable LLM fallback for entity extraction
# Edit config.py: ENABLE_LLM_FALLBACK = False
```

---

### Issue: High memory usage (>4GB)

**Cause:** Large graph or model loaded in RAM

**Diagnosis:**
```bash
# Check memory
ps aux | grep streamlit
```

**Solutions:**
```bash
# Use smaller embedding model
# Edit config.py:
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim instead of 768-dim

# Reduce graph size (prune orphan nodes)
python scripts/prune_graph.py

# Use quantizedOllama model
ollama pull qwen2.5:7b-q4_0  # 4GB vs 14GB
```

---

### Issue: Streamlit app freezes/crashes

**Cause:** Blocking operations in main thread

**Solution:**
```python
# Use Streamlit caching for heavy operations
@st.cache_resource
def load_graph():
    return nx.read_json("data/tiger_brain.json")

# Use spinner for long operations
with st.spinner("Processing..."):
    results = retriever.retrieve(query)
```

---

## Data Quality Issues

### Issue: Faculty bio is "Not available"

**Cause:** Crawl failed or bio not on page

**Diagnosis:**
```bash
# Check raw data
cat data/rit_data_v2.json | jq '.[] | select(.name=="Thomas Kinsman")'
```

**Solution:**
```bash
# Manual patching
python scripts/patch_kinsman.py

# Or re-crawl specific faculty
python src/crawlers/smart_crawler.py --url="https://www.rit.edu/directory/..."
```

---

### Issue: Duplicate nodes in graph

**Cause:** Entity resolution failed

**Diagnosis:**
```bash
# Check for duplicates
python scripts/debug_duplicates.py
```

**Solution:**
```bash
# Update entity mappings
# Edit data/entity_mappings.json:
{
  "faculty": {
    "c. kanan": "faculty_christopher_kanan",
    "chris kanan": "faculty_christopher_kanan"
  }
}

# Rebuild graph
python src/knowledge_graph/graph_builder.py
```

---

### Issue: Vector search returns irrelevant results

**Cause:** Embedding model mismatch or poor query

**Diagnosis:**
```python
# Test embeddings directly
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
emb1 = model.encode("computer vision research")
emb2 = model.encode("machine learning")

from scipy.spatial.distance import cosine
print(f"Similarity: {1 - cosine(emb1, emb2):.3f}")
```

**Solutions:**
```bash
# Use better embedding model
# Edit config.py:
EMBEDDING_MODEL = "all-mpnet-base-v2"  # Slower but more accurate

# Rebuild vector DB
rm -rf data/chroma/
python main.py load
```

---

## Integration Problems

### Issue: API rate limiting from RIT servers

**Cause:** Too many crawl requests

**Solution:**
```bash
# Increase crawl delay
# Edit config.py:
CRAWL_DELAY = 2.0  # Wait 2s between requests

# Use cached data
# Don't re-crawl if data/rit_data_v2.json exists
```

---

### Issue: PDF distillation fails

**Cause:** Corrupted PDF or unsupported format

**Diagnosis:**
```bash
# Test PDF manually
python -c "import fitz; doc = fitz.open('paper.pdf'); print(len(doc))"
```

**Solution:**
```bash
# Re-download PDF
wget -O paper.pdf "https://arxiv.org/pdf/..."

# Skip corrupted PDFs
# Add to .gitignore or delete
```

---

### Issue: Streamlit port 8501 already in use

**Cause:** Another Streamlit instance running

**Solution:**
```bash
# Find and kill process
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run src/ui/app.py --server.port 8502
```

---

## Debugging Techniques

### Enable Debug Logging

```python
# Add to main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Inspect Graph Interactively

```python
import networkx as nx

graph = nx.read_json("data/tiger_brain.json")

# Find specific node
node_data = graph.nodes["faculty_christopher_kanan"]
print(node_data)

# Find neighbors
neighbors = list(graph.neighbors("faculty_christopher_kanan"))
print(neighbors[:5])

# Check connectivity
print(nx.is_connected(graph))
```

### Test Components Independently

```bash
# Test crawler
python -m src.crawlers.smart_crawler

# Test graph builder
python -m src.knowledge_graph.graph_builder

# Test retriever
python scripts/test_retrieval.py
```

---

**End of Documentation**

For further assistance, file an issue on the repository.
