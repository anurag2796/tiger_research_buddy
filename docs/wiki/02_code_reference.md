# 02 - Code Reference

**Last Updated:** February 23, 2026  
**Purpose:** Complete module-by-module code walkthrough

---

## Recent Patch Notes (Feb 22–23, 2026)

| Module | File | Change | Bug # |
|--------|------|--------|---------|
| `DeepDistiller` | `processors/pdf_distiller.py` | `extract_text_async()` wrapped in full `try/except`; `isinstance(result, dict)` type guard added at L70–84 | Bug 1, 5 |
| `VectorStore` | `database/vector_store.py` | `TigerEmbeddingFunction.__init__()` runs warmup encode to force meta-tensor materialization | Bug 2 |
| `PaperDownloader` | `crawlers/paper_downloader_v3.py` | `download_pdf()` has 3-retry loop; `_is_author_match()` enforces first-name equality; `extract_text()` L318–337 has `isinstance` type guard | Bug 3, 4, 7 |
| `ScholarCrawler` | `crawlers/scholar_crawler.py` | `enrich_faculty_data()` uses index-based writes — workers return `(idx, copy, data)`, never mutate shared list | Bug 6 |
| Prompts | `data/prompts/*.md` | Anti-hallucination guards, structured output rules, and chain-of-density summarization added across `role.md`, `analyzer.md`, `critique.md`, `skills.md`, `chain_of_density.md` | — |

---

## Table of Contents

1. [Module Overview](#module-overview)
2. [Crawlers (`src/crawlers`)](#crawlers-srccrawlers)
3. [Database Layer (`src/database`)](#database-layer-srcdatabase)
4. [Knowledge Graph (`src/knowledge_graph`)](#knowledge-graph-srcknowledge_graph)
5. [Retrieval System ` (`src/retrieval`)](#retrieval-system-srcretrieval)
6. [Generation (`src/generation`)](#generation-srcgeneration)
7. [Chatbot (`src/chatbot`)](#chatbot-srcchatbot)
8. [UI (`src/ui`)](#ui-srcui)
9. [Utilities (`src/utils`)](#utilities-srcutils)

---

## Module Overview

```
src/
├── chatbot/
│   ├── ollama_client.py    # Local LLM client with persona support
│   ├── gemini_client.py    # Cloud LLM fallback (optional)
│   └── query_engine.py     # Chat session + context management
│
├── crawlers/
│   ├── smart_crawler.py        # LLM-based web scraper
│   ├── scholar_crawler.py      # Google Scholar enrichment (multithreaded)
│   ├── paper_downloader_v3.py  # PDF downloader (ArXiv + Semantic Scholar)
│   └── extended_crawler.py     # Multi-college crawler extension
│
├── processors/
│   └── pdf_distiller.py    # DeepDistiller: PDF → TigerCard 2.0 JSON
│
├── database/
│   ├── vector_store.py     # ChromaDB wrapper + BM25 indexing
│   └── lance_manager.py    # LanceDB wrapper (planned migration)
│
├── knowledge_graph/
│   ├── graph_builder.py    # Main graph assembly + export
│   ├── entity_resolver.py  # Canonical ID resolution + fuzzy matching
│   └── analytics.py        # Graph metrics (PageRank, centrality)
│
├── retrieval/
│   └── hybrid_retriever.py # Vector + BM25 + RRF fusion
│
├── generation/
│   └── synthesizer.py      # LLM response formatter + citation builder
│
web_app.py                  # Streamlit UI (main entry point)
run_pipeline.py             # Pipeline orchestrator (6 stages)
main.py                     # CLI utilities
```

---

## Crawlers (`src/crawlers`)

### smart_crawler.py

**Purpose:** LLM-powered web scraper that extracts faculty profiles from RIT websites without brittle CSS selectors.

**Key Classes:**

#### `SmartCrawler`
```python
class SmartCrawler:
    """V2 Crawler using NetworkX + LLM for robust extraction."""
    
    def __init__(self, start_url: str, max_pages: int = 100):
        self.start_url = start_url
        self.max_pages = max_pages
        self.visited = set()
        self.graph = nx.DiGraph()  # Site structure
        self.llm_client = get_ollama_client()
```

**Core Methods:**

##### `crawl_bfs() -> Tuple[nx.DiGraph, List[dict]]`
Crawls the site using breadth-first search.

```python
def crawl_bfs(self):
    queue = [self.start_url]
    faculty_data = []
    
    while queue and len(self.visited) < self.max_pages:
        url = queue.pop(0)
        if url in self.visited:
            continue
            
        # Fetch page
        html = self._fetch_page(url)
        
        # Extract structure
        links = self._extract_links(html, url)
        for link in links:
            self.graph.add_edge(url, link)
            queue.append(link)
        
        # Semantic extraction (LLM)
        if self._is_faculty_page(url):
            profile = self.extract_profile_data(url, html)
            if profile:
                faculty_data.append(profile)
        
        self.visited.add(url)
    
    return self.graph, faculty_data
```

##### `extract_profile_data(url: str, html: str) -> Optional[dict]`
Uses LLM to parse faculty information from raw HTML.

```python
def extract_profile_data(self, url: str, text_content: str) -> Optional[dict]:
    schema = {
        "name": "Full name",
        "title": "Job title",
        "department": "Department name",
        "bio": "Biography text",
        "email": "Email address",
        "research_interests": ["interest1", "interest2"]
    }
    
    prompt = f"""
    Extract faculty profile information from this HTML text.
    Return ONLY valid JSON matching this schema:
    {json.dumps(schema, indent=2)}
    
    HTML Content:
    {text_content[:4000]}  # First 4000 chars
    
    JSON:
    """
    
    response = self.llm_client.generate(prompt, system_prompt="You are a JSON extractor.")
    
    # Clean and parse JSON
    cleaned = self._clean_json_response(response)
    return json.loads(cleaned)
```

**Helper Methods:**

```python
def _is_faculty_page(self, url: str) -> bool:
    """Heuristic to identify faculty profile pages."""
    keywords = ['people', 'faculty', 'profile', 'bio', 'cv']
    return any(kw in url.lower() for kw in keywords)

def _clean_html(self, html: str) -> str:
    """Remove scripts, styles, nav elements."""
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    return soup.get_text(separator='\n', strip=True)
```

**Usage Example:**
```python
from src.crawlers.smart_crawler import SmartCrawler

crawler = SmartCrawler(
    start_url="https://www.rit.edu/computing/faculty-staff",
    max_pages=50
)

site_graph, faculty_profiles = crawler.crawl_bfs()

# Save results
nx.write_gml(site_graph, "data/site_graph.gml")
with open("data/rit_data_v2.json", "w") as f:
    json.dump(faculty_profiles, f, indent=2)
```

---

## Database Layer (`src/database`)

### vector_store.py

**Purpose:** ChromaDB wrapper for semantic search over faculty and research data.

> **Feb 22 Patch:** `TigerEmbeddingFunction.__init__()` now runs a warmup encode (`self.model.encode(["warmup"])`) after model load. This forces PyTorch to materialize meta-tensor weights in the main thread before any ChromaDB internal thread calls `encode()`. Without this, the first real call would crash with `Cannot copy out of meta tensor; no data!` and leave the vector store empty.

#### `VectorStore`
```python
class VectorStore:
    """Vector database for semantic search over research data."""
    
    def __init__(self, config: CrawlConfig = RESTRICTED_CONFIG):
        self.config = config
        self.client = None
        self.collection = None
        self._initialized = False
```

**Key Methods:**

##### `process_data_into_documents(data: dict) -> list[dict]`
Helper function to transform raw JSON data into the standardized document format used by both ChromaDB and BM25.

##### `initialize()`
Sets up persistent ChromaDB client.

```python
def initialize(self):
    if self._initialized:
        return
        
    chromadb = _get_chromadb()
    self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    self.collection = self.client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_embedding_function(),
        metadata={"description": "RIT research data"}
    )
    
    self._initialized = True
```

##### `add_documents(documents: list[dict])`
Batch insert documents with embeddings.

```python
def add_documents(self, documents: list[dict]):
    ids, contents, metadatas = [], [], []
    
    for i, doc in enumerate(documents):
        doc_id = doc.get("id", f"doc_{i}")
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        
        # ChromaDB requires string values
        clean_metadata = {}
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                clean_metadata[k] = json.dumps(v)
            else:
                clean_metadata[k] = str(v) if v else ""
        
        ids.append(doc_id)
        contents.append(content)
        metadatas.append(clean_metadata)
    
    # Upsert handles duplicates
    self.collection.upsert(
        ids=ids,
        documents=contents,
        metadatas=metadatas
    )
```

##### `search(query: str, n_results: int = 5) -> list[dict]`
Semantic similarity search.

```python
def search(self, query: str, n_results: int = 5, doc_type: Optional[str] = None):
    where_filter = {"doc_type": doc_type} if doc_type else None
    
    results = self.collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter
    )
    
    # Format results
    formatted = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            formatted.append({
                "content": doc,
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
    
    return formatted
```

**Document Schema:**
```python
document = {
    "id": "prof_christopher_kanan",  # Unique identifier
    "content": """Professor: Christopher Kanan
Title: Associate Professor
Department: Computing
Bio: Dr. Kanan's research focuses on computer vision...
Research Interests: Computer Vision, Deep Learning, Brain-Inspired AI
Tags: computer_vision, deep_learning, artificial_intelligence""",
    "metadata": {
        "doc_type": "professor",  # professor | paper | research_area
        "name": "Christopher Kanan",
        "department": "Computing",
        "tags": ["computer_vision", "deep_learning"],
        "citations": "5000",
        "h_index": "42"
    }
}
```

---

## Knowledge Graph (`src/knowledge_graph`)

### graph_builder.py

**Purpose:** Constructs the unified TigerBrain knowledge graph by merging site structure with semantic research data.

#### `GraphBuilder`
```python
class GraphBuilder:
    """Builds the unified knowledge graph from multiple sources."""
    
    def __init__(self, site_graph_path: str, faculty_json_path: str, cards_dir: str):
        self.site_graph_path = Path(site_graph_path)
        self.faculty_json_path = Path(faculty_json_path)
        self.cards_dir = Path(cards_dir)
        self.graph = nx.Graph()
        self.resolver = EntityResolver()
```

**Build Pipeline:**

##### `build() -> nx.Graph`
Main orchestration method.

```python
def build(self) -> nx.Graph:
    console.print("[bold blue]🔨 Building TigerBrain Graph...[/]")
    
    # 1. Load structural skeleton
    self.load_site_graph()
    
    # 2. Add rich faculty data
    self.hydrate_faculty()
    
    # 3. Merge research papers
    self.merge_research_cards()
    
    # 4. Infer implicit edges
    self.infer_faculty_concepts()
    
    # 5. Clean and validate
    self.sanitize_graph()
    
    console.print(f"[green]✓ Graph complete: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges[/]")
    
    return self.graph
```

##### `load_site_graph()`
Loads the site structure created by SmartCrawler.

```python
def load_site_graph(self):
    if not self.site_graph_path.exists():
        console.print("[yellow]Site graph not found, creating empty graph[/]")
        return
    
    site_g = nx.read_gml(str(self.site_graph_path))
    
    # Merge into main graph
    for node, data in site_g.nodes(data=True):
        self.graph.add_node(node, **data)
    for u, v, data in site_g.edges(data=True):
        self.graph.add_edge(u, v, **data)
```

##### `hydrate_faculty()`
Enriches faculty nodes with full profile data.

```python
def hydrate_faculty(self):
    if not self.faculty_json_path.exists():
        return
    
    with open(self.faculty_json_path) as f:
        faculty_data = json.load(f)
    
    for prof in faculty_data:
        name = prof.get("name", "")
        if not name:
            continue
        
        # Create canonical ID
        faculty_id = f"faculty_{name.lower().replace(' ', '_')}"
        
        # Add/update node
        self.graph.add_node(
            faculty_id,
            type="faculty",
            label=name,
            name=name,
            title=prof.get("title", ""),
            dept=prof.get("department", ""),
            bio=prof.get("bio", ""),
            email=prof.get("email", ""),
            interests=prof.get("research_interests", [])
        )
```

##### `merge_research_cards()`
Integrates PDF-extracted research cards.

```python
def merge_research_cards(self):
    json_files = list(self.cards_dir.glob("*.json"))
    
    for json_file in track(json_files, description="Merging Knowledge..."):
        with open(json_file) as f:
            card = json.load(f)
        
        # 1. Add Paper node
        paper_title = card.get("title", "Unknown")
        paper_id = f"paper_{paper_title.lower().replace(' ', '_')}"[:50]
        
        self.graph.add_node(
            paper_id,
            type="paper",
            label=paper_title,
            year=card.get("year", ""),
            abstract=card.get("core_problem", "")
        )
        
        # 2. Link to authors (with fuzzy matching)
        authors = card.get("authors", [])
        for author_name in authors:
            faculty_id = self.resolver.resolve_faculty(author_name)
            if faculty_id:
                self.graph.add_edge(faculty_id, paper_id, type="AUTHORED")
        
        # 3. Extract and link concepts
        entities = card.get("entities", {})
        for category, items in entities.items():
            for item in items:
                concept_id = f"concept_{item.lower().replace(' ', '_')}"
                self.graph.add_node(concept_id, type="concept", name=item, category=category)
                self.graph.add_edge(paper_id, concept_id, type="MENTIONS")
```

**Entity Resolution:**

The `EntityResolver` handles name variations:

```python
class EntityResolver:
    def resolve_faculty(self, name: str) -> Optional[str]:
        # 1. Try exact match
        canonical = self.canonical_map.get(name.lower())
        if canonical:
            return canonical
        
        # 2. Fuzzy matching (TheFuzz)
        matches = process.extract(name, self.all_names, limit=1)
        if matches and matches[0][1] > 90:  # 90% similarity
            return self.canonical_map[matches[0][0]]
        
        # 3. Try last name only
        last_name = name.split()[-1]
        for full_name, canonical_id in self.canonical_map.items():
            if last_name.lower() in full_name:
                return canonical_id
        
        return None
```

---

## Retrieval System (`src/retrieval`)

### hybrid_retriever.py

**Purpose:** Implements Hybrid Search combining Vector Search (ChromaDB) and Keyword Search (BM25) using Reciprocal Rank Fusion (RRF).

#### `HybridRetriever`
```python
class HybridRetriever:
    """Hybrid Retriever that combines Vector Search and BM25 using Reciprocal Rank Fusion (RRF)."""
    
    def __init__(self, vector_store: VectorStore, documents: Optional[List[Dict]] = None):
        self.vector_store = vector_store
        if documents:
            self.index_bm25(documents)
```

**Key Methods:**

##### `index_bm25(documents: List[Dict])`
Builds an in-memory BM25 index from the provided documents.

##### `hybrid_search(query: str, k: int = 50, rrf_k: int = 60) -> List[Dict]`
Performs RRF fusion of vector and keyword results.

```python
def hybrid_search(self, query: str, k: int = 50, rrf_k: int = 60) -> List[Dict]:
    # 1. Get results from both retrievers
    vector_results = self._search_vector(query, k=50)
    bm25_results = self._search_bm25(query, k=50)
    
    # 2. Combine using RRF
    # Score = 1 / (rank + k)
    
    # 3. Sort and return
    return reranked_results[:k]
```



---

## Generation (`src/generation`)

### synthesizer.py

**Purpose:** Generates human-readable responses with strict citation enforcement.

#### `ResponseSynthesizer`
```python
class ResponseSynthesizer:
    """Generates cited responses using local LLM."""
    
    def __init__(self):
        self.client = get_ollama_client()
```

##### `synthesize(query: str, results: Dict) -> str`
Main synthesis pipeline.

```python
def synthesize(self, query: str, results: Dict[str, Any]) -> str:
    # 1. Format context from retrieval results
    context_str, sources = self._format_context(results)
    
    # 2. Build structured prompt
    system_prompt = self._get_system_prompt()
    user_prompt = f"""
Query: {query}

Context:
{context_str}

Generate a helpful response following the format:
1. Direct Answer
2. Key Faculty (if applicable)
3. Research Areas
4. Next Steps
"""
    
    # 3. Generate response
    response = self.client.generate(
        prompt=user_prompt,
        system_prompt=system_prompt
    )
    
    # 4. Format output with sources
    return self._format_output(response, sources)
```

##### `_format_context(results: Dict) -> Tuple[str, List]`
Converts retrieval results into LLM context.

```python
def _format_context(self, results: Dict) -> Tuple[str, List]:
    context_parts = []
    sources = []
    
    # Graph results
    for i, res in enumerate(results.get("graph_results", [])[:5]):
        data = res.get("data", {})
        context_parts.append(f"""
Faculty: {data.get('name', 'Unknown')}
Title: {data.get('title', '')}
Bio: {data.get('bio', '')[:300]}
""")
        sources.append({
            "type": "faculty",
            "name": data.get('name'),
            "url": data.get('profile_url')
        })
    
    # Vector results
    for i, res in enumerate(results.get("vector_results", [])[:5]):
        context_parts.append(f"Document: {res['content'][:200]}")
        sources.append({
            "type": "document",
            "id": res['id']
        })
    
    return "\n---\n".join(context_parts), sources
```

---

## Chatbot (`src/chatbot`)

### ollama_client.py

**Purpose:** Abstraction layer for local Ollama LLM with persona management.

#### `OllamaClient`
```python
class OllamaClient:
    """Client for interacting with local Ollama LLM."""
    
    def __init__(self, model: str = "tigerbuddy", persona: str = "tiger"):
        self.model = model
        self.persona = persona
        self._persona_prompts = {}
```

##### `initialize()`
Checks if Ollama server is running and models are available.

```python
def initialize(self):
    try:
        models_response = ollama.list()
        self._available_models = [m.model for m in models_response.models]
        
        if not self._available_models:
            raise RuntimeError("No models found. Run: ollama pull tigerbuddy")
        
        console.print(f"[green]✓ Ollama ready ({len(self._available_models)} models)[/]")
        self._initialized = True
        
    except Exception as e:
        raise RuntimeError(f"Ollama not running. Start: brew services start ollama")
```

##### `set_persona(persona: str)`
Switches between chat personas (tiger, analyzer, critique).

```python
def set_persona(self, persona: str):
    valid_personas = ["tiger", "analyzer", "critique"]
    if persona not in valid_personas:
        raise ValueError(f"Unknown persona: {persona}")
    
    self.persona = persona
    console.print(f"[cyan]Switched to {persona} persona[/]")
```

##### `generate(prompt: str, context: str = None, system_prompt: str = None) -> str`
Core generation method.

```python
def generate(self, prompt: str, context: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
    if not self._initialized:
        self.initialize()
    
    messages = []
    
    # Load persona prompt if no custom system prompt
    if not system_prompt:
        system_prompt = self._load_persona_prompt()
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Construct user message
    user_content = ""
    if context:
        user_content += f"Context:\n{context}\n\n"
    user_content += prompt
    
    messages.append({"role": "user", "content": user_content})
    
    # Call Ollama
    try:
        response = ollama.chat(model=self.model, messages=messages)
        return response['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"
```

---

## UI (`src/ui`)

### app.py

**Purpose:** Streamlit web interface for interacting with TigerBrain.

**Key Components:**

##### Initialization & Caching
```python
@st.cache_resource
def get_engine():
    """Load backend components once (cached in memory)."""
    db_manager = LanceManager()
    
    retriever = HybridRetriever(
        vector_db=db_manager,
        graph_path="data/tiger_brain.json"
    )
    
    synthesizer = ResponseSynthesizer()
    return retriever, synthesizer

retriever, synthesizer = get_engine()
```

##### Chitchat Handler
```python
if prompt := st.chat_input("Ex: Who works on Spiking Neural Networks?"):
    # Check for greetings
    low_prompt = prompt.lower().strip()
    if low_prompt in ["hi", "hello", "hey", "who are you"]:
        response = "Hello! I'm your AI Research Advisor..."
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.stop()  # Skip retrieval pipeline
```

##### Main Query Flow
```python
with st.spinner("Analyzing Research Graph..."):
    try:
        # 1. Retrieve
        results = retriever.retrieve(prompt, limit=5)
        
        # 2. Synthesize
        full_response = synthesizer.synthesize(prompt, results)
        
        # 3. Display
        st.markdown(full_response)
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
```

---

**Next:** [API Reference →](./03_api_reference.md)
