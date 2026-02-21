# 03 - API Reference

**Last Updated:** February 9, 2026  
**Purpose:** Complete API documentation for all public interfaces

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Vector Store API](#vector-store-api)
3. [Hybrid Retriever API](#hybrid-retriever-api)
4. [Graph Builder API](#graph-builder-api)
5. [Ollama Client API](#ollama-client-api)
6. [Response Synthesizer API](#response-synthesizer-api)
7. [Entity Extractor API](#entity-extractor-api)
8. [Error Handling](#error-handling)

---

## API Overview

All TigerBrain APIs follow these conventions:

**Naming:** PEP 8 compliant (snake_case for functions/methods, PascalCase for classes)  
**Type Hints:** Full type annotations using `typing` module  
**Docstrings:** Google-style docstrings  
**Error Handling:** Raises descriptive exceptions, never silent failures

---

## Vector Store API

### Class: `VectorStore`

**Module:** `src.database.vector_store`  
**Purpose:** Persistent semantic search over research documents

#### Constructor

```python
def __init__(self) -> None:
    """Initialize VectorStore (lazy - call initialize() explicitly)."""
```

**Example:**
```python
from src.database.vector_store import VectorStore

store = VectorStore()
store.initialize()  # Connects to ChromaDB
```

---

#### Methods

##### `initialize() -> None`

Initializes the ChromaDB client and loads/creates the collection.

**Parameters:** None  
**Returns:** None  
**Raises:** `RuntimeError` if ChromaDB cannot be initialized  
**Side Effects:** Creates `data/chroma/` directory if missing

**Example:**
```python
store = VectorStore()
store.initialize()
# Output: "✓ Vector store ready (1523 documents)"
```

---

##### `add_documents(documents: list[dict]) -> None`

Batch insert documents with automatic embedding generation.

**Parameters:**
- `documents` (list[dict]): List of document dicts with keys:
  - `id` (str): Unique identifier
  - `content` (str): Text to embed
  - `metadata` (dict): Arbitrary metadata (values must be JSON-serializable)

**Returns:** None  
**Raises:** `ValueError` if document format is invalid  
**Side Effects:** Upserts to persistent ChromaDB storage

**Example:**
```python
docs = [
    {
        "id": "prof_kanan",
        "content": "Dr. Kanan works on computer vision...",
        "metadata": {
            "doc_type": "professor",
            "name": "Christopher Kanan",
            "department": "Computing"
        }
    }
]

store.add_documents(docs)
# Output: "✓ Added 1 documents to vector store"
```

---

##### `search(query: str, n_results: int = 5, doc_type: Optional[str] = None) -> list[dict]`

Semantic similarity search using cosine distance.

**Parameters:**
- `query` (str): Natural language search query
- `n_results` (int, default=5): Number of results to return
- `doc_type` (Optional[str]): Filter by metadata `doc_type` field

**Returns:** List of dicts with keys:
- `content` (str): Document text
- `id` (str): Document ID
- `metadata` (dict): Document metadata
- `distance` (float): Cosine distance (lower = more similar)

**Raises:** None (returns empty list if no results)

**Example:**
```python
results = store.search("computer vision research", n_results=3)

for res in results:
    print(f"ID: {res['id']}")
    print(f"Distance: {res['distance']:.3f}")
    print(f"Content: {res['content'][:100]}...")
    print()
```

**Output:**
```
ID: prof_christopher_kanan
Distance: 0.234
Content: Professor: Christopher Kanan
Title: Associate Professor
Department: Computing
Bio: Dr. Kanan's research...

ID: paper_making_it_work
Distance: 0.312
Content: Publication: Making It Work...
```

---

##### `get_stats() -> dict`

Returns statistics about the vector store.

**Parameters:** None  
**Returns:** Dict with keys:
- `total_documents` (int): Total documents in collection
- `collection_name` (str): Name of ChromaDB collection

**Example:**
```python
stats = store.get_stats()
print(stats)
# {'total_documents': 1523, 'collection_name': 'rit_research'}
```

---

##### `clear() -> None`

Deletes all documents from the collection (destructive operation).

**Parameters:** None  
**Returns:** None  
**Raises:** `RuntimeError` if collection deletion fails  
**Side Effects:** Permanently deletes all vectors

**Example:**
```python
store.clear()
# Output: "Cleared vector store"
```

---

## Hybrid Retriever API

### Class: `HybridRetriever`

**Module:** `src.retrieval.hybrid_retriever`  
**Purpose:** Orchestrates Hybrid Search using Vector (ChromaDB) + Keyword (BM25) with Reciprocal Rank Fusion (RRF).

#### Constructor

```python
def __init__(
    self,
    vector_store: VectorStore,
    documents: Optional[List[Dict]] = None
) -> None:
    """
    Initialize HybridRetriever.
    
    Args:
        vector_store: Initialized VectorStore instance
        documents: List of documents to index for BM25 (optional)
    """
```

**Example:**
```python
from src.database.vector_store import get_vector_store
from src.retrieval.hybrid_retriever import HybridRetriever

vector_store = get_vector_store()
# Assuming 'documents' is a list of dicts loaded from JSON
retriever = HybridRetriever(vector_store, documents)
```

---

#### Methods

##### `hybrid_search(query: str, k: int = 50, rrf_k: int = 60) -> List[Dict]`

Performs the hybrid search using RRF.

**Parameters:**
- `query` (str): User query
- `k` (int, default=50): Number of results to return
- `rrf_k` (int, default=60): RRF constant

**Returns:** List of dicts (documents) with added scores/ranks.

**Example:**
```python
results = retriever.hybrid_search("Who works on AI?")
for res in results[:5]:
    print(f"{res['metadata']['title']} (Score: {res['rrf_score']:.4f})")
```

##### `index_bm25(documents: List[Dict]) -> None`

Builds the BM25 index from the given documents.

**Parameters:**
- `documents` (List[Dict]): Documents to index.

**Returns:** None

---

## Graph Builder API

### Class: `GraphBuilder`

**Module:** `src.knowledge_graph.graph_builder`  
**Purpose:** Constructs the unified knowledge graph from multiple data sources

#### Constructor

```python
def __init__(
    self,
    site_graph_path: str,
    faculty_json_path: str,
    cards_dir: str
) -> None:
    """
    Initialize GraphBuilder.
    
    Args:
        site_graph_path: Path to site_graph.gml file
        faculty_json_path: Path to rit_data_v2.json
        cards_dir: Directory containing research card JSONs
    """
```

**Example:**
```python
from src.knowledge_graph.graph_builder import GraphBuilder

builder = GraphBuilder(
    site_graph_path="data/site_graph.gml",
    faculty_json_path="data/rit_data_v2.json",
    cards_dir="data/research_cards/"
)

graph = builder.build()
```

---

#### Methods

##### `build() -> networkx.Graph`

Main orchestration method that runs the entire graph construction pipeline.

**Parameters:** None  
**Returns:** NetworkX Graph object  
**Raises:** `FileNotFoundError` if source files missing  
**Side Effects:** None (pure function)

**Pipeline Steps:**
1. Load site graph skeleton
2. Hydrate faculty nodes
3. Merge research cards
4. Infer faculty-concept relationships
5. Sanitize and validate

**Example:**
```python
graph = builder.build()
print(f"Nodes: {graph.number_of_nodes()}")
print(f"Edges: {graph.number_of_edges()}")
```

---

##### `save(output_path: str, format: str = "json") -> None`

Saves the graph to disk.

**Parameters:**
- `output_path` (str): Output file path
- `format` (str, default="json"): Format ("json", "gml", "graphml")

**Returns:** None  
**Raises:** `ValueError` if format unsupported

**Example:**
```python
builder.save("data/tiger_brain.json", format="json")
builder.save("data/tiger_brain.gml", format="gml")
```

---

## Ollama Client API

### Class: `OllamaClient`

**Module:** `src.chatbot.ollama_client`  
**Purpose:** Interface to local Ollama LLM with persona management

#### Constructor

```python
def __init__(
    self,
    model: str = "tigerbuddy",
    persona: str = "tiger"
) -> None:
    """
    Initialize OllamaClient.
    
    Args:
        model: Ollama model name
        persona: Persona to use ("tiger", "analyzer", "critique")
    """
```

**Example:**
```python
from src.chatbot.ollama_client import OllamaClient

client = OllamaClient(model="tigerbuddy", persona="tiger")
client.initialize()
```

---

#### Methods

##### `generate(prompt: str, context: Optional[str] = None, system_prompt: Optional[str] = None) -> str`

Generates a text response from the LLM.

**Parameters:**
- `prompt` (str): User prompt
- `context` (Optional[str]): Additional context to inject
- `system_prompt` (Optional[str]): Override default persona prompt

**Returns:** str (LLM response)  
**Raises:** `RuntimeError` if Ollama server not running

**Example:**
```python
response = client.generate(
    prompt="Explain reinforcement learning briefly.",
    context="The user is an undergraduate CS student."
)

print(response)
```

**Output:**
```
Reinforcement Learning is like training a dog with treats! The algorithm learns by trying actions and getting rewards (positive feedback) or penalties (negative feedback). Over time, it learns which actions lead to the best outcomes. 🐕

In technical terms, an agent interacts with an environment, takes actions, and receives rewards...
```

---

##### `set_persona(persona: str) -> None`

Switches the active persona.

**Parameters:**
- `persona` (str): One of "tiger", "analyzer", "critique"

**Returns:** None  
**Raises:** `ValueError` if persona unknown

**Example:**
```python
client.set_persona("critique")
response = client.generate("Explain my research idea about using CNNs for audio.")
# Response will be in critical/Socratic style
```

---

## Response Synthesizer API

### Class: `ResponseSynthesizer`

**Module:** `src.generation.synthesizer`  
**Purpose:** Generates structured, cited responses from retrieval results

#### Constructor

```python
def __init__(self) -> None:
    """Initialize ResponseSynthesizer."""
```

---

#### Methods

##### `synthesize(query: str, results: Dict[str, Any]) -> str`

Generates a formatted response with citations.

**Parameters:**
- `query` (str): Original user query
- `results` (dict): Output from HybridRetriever.retrieve()
- `use_cod` (bool, default=False): Enable Chain of Density prompting for deeper analysis

**Returns:** str (Markdown-formatted response)  
**Raises:** None (degrades gracefully on LLM errors)

**Example:**
```python
from src.generation.synthesizer import ResponseSynthesizer

synthesizer = ResponseSynthesizer()
results = retriever.retrieve("Who works on AI safety?")
response = synthesizer.synthesize("Who works on AI safety?", results)

print(response)
```

**Output:**
```markdown
## Direct Answer
Based on my database, **Dr. Christopher Kanan** and **Dr. Cecilia Alm** have published work related to AI safety and robustness.

## Key Faculty
1. **Dr. Christopher Kanan** 🧠
   - Focus: Computer Vision, Robustness
   - Relevant Work: Adversarial robustness in neural networks

2. **Dr. Cecilia Alm** 💬
   - Focus: NLP, Ethical AI
   - Relevant Work: Bias detection in language models

## Research Areas
- Adversarial Machine Learning
- AI Ethics & Fairness
- Robust AI Systems

## Next Steps
- Check out Dr. Kanan's 2022 paper on "Model Robustness via Test-Time Augmentation"
- Email Dr. Alm at ca@rit.edu to discuss NLP ethics projects

---
**Sources:**
[1] Faculty Profile: Christopher Kanan
[2] Research Paper: Adversarial Robustness (2022)
```

---



---

## Error Handling

### Common Exceptions

All APIs raise standard Python exceptions:

| Exception | Cause | Handling |
|-----------|-------|----------|
| `FileNotFoundError` | Missing data files | Check paths, run setup scripts |
| `RuntimeError` | Ollama/ChromaDB not running | Start services |
| `ValueError` | Invalid parameters | Check API docs for valid values |
| `JSONDecodeError` | Corrupted data files | Re-run crawlers/builders |

**Example Error Handler:**
```python
from src.retrieval.hybrid_retriever import HybridRetriever
import logging

logger = logging.getLogger(__name__)

try:
    retriever = HybridRetriever(
        vector_db=vector_store,
        graph_path="data/tiger_brain.json"
    )
    results = retriever.retrieve("Who works on AI?")
except FileNotFoundError as e:
    logger.error(f"Graph file missing: {e}")
    logger.info("Run: python src/knowledge_graph/graph_builder.py")
except RuntimeError as e:
    logger.error(f"Service unavailable: {e}")
    logger.info("Start Ollama: brew services start ollama")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
```

---

**Next:** [Configuration →](./04_configuration.md)
