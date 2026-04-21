"""Vector store using ChromaDB for semantic search."""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..utils.config import CrawlConfig, RESTRICTED_CONFIG, EMBEDDING_MODEL, DATA_DIR
from ..utils.timer import Timer
from ..utils.hardware import get_embedding_device  # X4 fix: dynamic device detection

console = Console()

# Lazy imports for heavy dependencies
_chromadb = None
_embedding_function = None


def _get_chromadb():
    """Lazy load chromadb."""
    global _chromadb
    if _chromadb is None:
        import chromadb
        _chromadb = chromadb
    return _chromadb


def _get_embedding_function():
    """Lazy load embedding function with hardware-aware device selection.

    Device is determined by ``hardware.get_embedding_device()`` which:
    - Returns "cpu" on Apple Silicon (MPS has a meta-tensor bug with nomic)
    - Returns "cuda" on Jetson Orin / any CUDA host
    - Returns "cpu" as universal fallback
    Override with the ``EMBEDDING_DEVICE`` env var if needed.

    A secondary CUDA availability check here ensures we never pass device='cuda'
    to SentenceTransformer when torch.cuda.is_available() is False, which would
    cause a hard crash instead of a graceful CPU fallback.
    """
    global _embedding_function
    if _embedding_function is None:
        try:
            from chromadb.utils import embedding_functions
            try:
                from sentence_transformers import SentenceTransformer
                # X4 fix: use hardware-aware device, not the inverted MPS check.
                device = get_embedding_device()

                # Fix 2: belt-and-suspenders CUDA validation
                if device == "cuda":
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            console.print(
                                "[yellow]WARNING: EMBEDDING_DEVICE resolved to 'cuda' but "
                                "torch.cuda.is_available()=False. Falling back to CPU. "
                                "Reinstall a Jetson-compatible PyTorch wheel to enable GPU.[/]"
                            )
                            device = "cpu"
                    except ImportError:
                        device = "cpu"

                console.print(f"[dim]Loading {EMBEDDING_MODEL} on device={device!r}[/]")
                _model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True, device=device)
                
                from chromadb import EmbeddingFunction, Documents, Embeddings
                class SafeTigerEmbeddingFunction(EmbeddingFunction):
                    def __init__(self, model):
                        self.model = model
                    def __call__(self, input: Documents) -> Embeddings:
                        return self.model.encode(list(input)).tolist()
                
                _embedding_function = SafeTigerEmbeddingFunction(_model)
                console.print(f"[green]Initialized {EMBEDDING_MODEL} embedding function (device={device!r})[/]")
            except NotImplementedError:
                # Catch the "Cannot copy out of meta tensor" MPS bug as a last resort.
                console.print(f"[yellow]PyTorch meta tensor issue detected. Falling back to default ONNX embeddings.[/]")
                _embedding_function = embedding_functions.DefaultEmbeddingFunction()
                
        except ImportError as e:
            console.print(f"[red]Failed to import chromadb or sentence-transformers: {e}[/]")
            raise
    return _embedding_function


class VectorStore:
    """Vector database for semantic search over research data."""
    
    def __init__(self, config: CrawlConfig = RESTRICTED_CONFIG):
        self.config = config
        self.client = None
        self.collection = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the vector store."""
        if self._initialized:
            return
            
        console.print("[bold blue]📦 Initializing vector store...[/]")
        
        # Get or create collection
        chromadb = _get_chromadb()
        self.client = chromadb.PersistentClient(path=str(self.config.CHROMA_DIR))
        
        self.collection = self.client.get_or_create_collection(
            name=self.config.COLLECTION_NAME,
            embedding_function=_get_embedding_function(),
            metadata={"description": "RIT research data"}
        )
        
        self._initialized = True
        console.print(f"[green]✓ Vector store ready ({self.collection.count()} documents)[/]")
    
    def add_documents(self, documents: list[dict]):
        """Add documents to the vector store."""
        if not self._initialized:
            self.initialize()
        
        if not documents:
            return
        
        ids = []
        contents = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get("id", f"doc_{i}")
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            # Ensure metadata values are strings (ChromaDB requirement)
            clean_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (list, dict)):
                    clean_metadata[k] = json.dumps(v)
                else:
                    clean_metadata[k] = str(v) if v else ""
            
            ids.append(doc_id)
            contents.append(content)
            metadatas.append(clean_metadata)
        
        # Upsert to handle duplicates

        with Timer(f"Upserting {len(documents)} docs to Chroma", use_rich=False):
            self.collection.upsert(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )
        
        console.print(f"[green]✓ Added {len(documents)} documents to vector store[/]")

    def add_idea(self, idea):
        """Add a single idea to the vector store."""
        content = f"""Idea: {idea.title}
Description: {idea.description}
Author: {idea.author_name}
College: {idea.college if idea.college else 'Unknown'}
Tags: {', '.join(idea.tags)}
Status: {idea.status}"""
        
        self.add_documents([{
            "id": f"idea_{idea.id}",
            "content": content,
            "metadata": {
                "doc_type": "idea",
                "title": idea.title,
                "author": idea.author_name,
                "college": idea.college,
                "tags": json.dumps(idea.tags),
                "status": idea.status,
                "created_at": idea.created_at
            }
        }])
    
    def add_research_cards(self, cards: list[dict]):
        """Add distilled Research Cards to vector store."""
        documents = []
        seen_ids = set()
        
        for card in cards:
            if "card_id" not in card:
                continue
            
            card_id = str(card["card_id"])
            if card_id in seen_ids:
                continue
            seen_ids.add(card_id)
                
            bib = card.get("bibliographic_data", {})
            core = card.get("core_content", {})
            kg = card.get("knowledge_graph", {})
            
            # Safely extract concepts
            concepts = []
            for n in kg.get('nodes', []):
                if isinstance(n, dict):
                    concepts.append(n.get('label', ''))
                elif isinstance(n, str):
                    concepts.append(n)
            
            # Safely extract outcomes
            outcomes = core.get('outcomes', [])
            if not isinstance(outcomes, list):
                outcomes = [str(outcomes)]
            
            # Construct rich semantic content
            content = f"""Title: {bib.get('title')}
Domain: {bib.get('primary_domain')}
Novelty: {core.get('novelty_claim')}
Methodology: {core.get('key_methodology')}
Outcomes: {', '.join(outcomes)}
Concepts: {', '.join(concepts)}
Abstract: {str(core.get('full_text_markdown', ''))[:1000]}..."""

            documents.append({
                "id": card_id,
                "content": content,
                "metadata": {
                    "doc_type": "research_card",
                    "title": bib.get("title", ""),
                    "year": str(bib.get("year", "")),
                    "domain": bib.get("primary_domain", ""),
                    "authors": json.dumps(bib.get("authors", []))
                }
            })
            
        if documents:
            console.print(f"[bold blue]📦 Indexing {len(documents)} Research Cards...[/]")
            self.add_documents(documents)

    def search(self, query: str, n_results: int = 5, doc_type: Optional[str] = None) -> list[dict]:
        """Search for similar documents."""
        if not self._initialized:
            self.initialize()
        
        # Build where filter if doc_type specified
        where_filter = None
        if doc_type:
            where_filter = {"doc_type": doc_type}
        
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
                    "id": results["ids"][0][i] if results["ids"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0
                })
        
        return formatted
    
    def clear(self):
        """Clear all documents from the collection."""
        if self._initialized and self.collection:
            # Delete the collection and recreate
            chromadb = _get_chromadb()
            self.client.delete_collection(self.config.COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=self.config.COLLECTION_NAME,
                embedding_function=_get_embedding_function()
            )
            console.print("[yellow]Cleared vector store[/]")
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        if not self._initialized:
            self.initialize()
        
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.config.COLLECTION_NAME
        }


def process_data_into_documents(data: dict):
    """Process raw data into document format for vector store using a generator."""
    from ..utils.tag_generator import generate_tags_for_professor, generate_tags_for_research_area, generate_tags_for_publication
    
    seen_ids = set()
    
    # Add research areas with tags
    for area in data.get("research_areas", []):
        doc_id = f"area_{area['name'].lower().replace(' ', '_').replace('/', '_')[:50]}"
        
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        
        # Generate tags
        tags = generate_tags_for_research_area(area)
        tag_names = [t[0] for t in tags[:15]]  # Top 15 tags
        
        # Build rich content
        faculty_names = [f.get("name", "") for f in area.get("faculty", [])][:10]
        
        content = f"""Research Area: {area['name']}
Description: {area.get('description', 'No description available')}
Tags: {', '.join(tag_names) if tag_names else 'computing, research'}
Faculty in this area: {', '.join(faculty_names) if faculty_names else 'See individual profiles'}
URL: {area.get('url', '')}"""
        
        yield {
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "research_area",
                "name": area["name"],
                "url": area.get("url", ""),
                "college": area.get("college", ""),
                "tags": json.dumps(tag_names)
            }
        }
    
    # Add faculty with tags
    for prof in data.get("faculty", []):
        doc_id = f"prof_{prof['name'].lower().replace(' ', '_').replace('/', '_')[:50]}"
        
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        
        # Generate tags
        tags = generate_tags_for_professor(prof)
        tag_names = [t[0] for t in tags[:15]]
        
        # Get scholar data
        scholar = prof.get("scholar", {})
        interests = scholar.get("interests", []) or prof.get("research_interests", [])
        pubs = scholar.get("publications", [])
        citations = scholar.get("citations", "Unknown")
        h_index = scholar.get("h_index", "Unknown")
        
        # Get profile data
        bio_val = prof.get("bio", "")
        bio = str(bio_val)[:500] if bio_val else ""
        research_areas = prof.get("research_areas", [])
        
        content = f"""Professor: {prof['name']}
Title: {prof.get('title', 'Faculty')}
Department: {prof.get('department', 'Computing')}
Bio: {bio if bio else 'Not available'}
Research Interests: {', '.join(interests) if interests else 'Not specified'}
Research Areas: {', '.join(research_areas) if research_areas else 'See RIT website'}
Tags: {', '.join(tag_names) if tag_names else 'faculty'}
Google Scholar Citations: {citations}
H-Index: {h_index}
Recent Publications: {', '.join(str(p.get('title', ''))[:100] for p in pubs[:5]) if pubs else 'Not available'}
Profile URL: {prof.get('profile_url', '')}
Email: {prof.get('email', '')}
Office: {prof.get('office', '')}
College: {prof.get('college', '')}"""
        
        yield {
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "professor",
                "name": prof["name"],
                "title": prof.get("title", ""),
                "url": prof.get("profile_url", ""),
                "email": prof.get("email", ""),
                "office": prof.get("office", ""),
                "tags": json.dumps(tag_names),
                "citations": str(citations),
                "h_index": str(h_index),
                "college": prof.get("college", "")
            }
        }
        
        # Also add publications as separate documents
        for i, pub in enumerate(pubs[:5]):  # Top 5 publications per professor
            pub_title = pub.get("title", "")
            if not pub_title:
                continue
                
            pub_id = f"pub_{prof['name'].lower().replace(' ', '_')[:20]}_{i}"
            
            if pub_id in seen_ids:
                continue
            seen_ids.add(pub_id)
            
            pub_tags = generate_tags_for_publication(pub)
            pub_tag_names = [t[0] for t in pub_tags[:10]]
            
            pub_content = f"""Publication: {pub_title}
Author: {prof['name']}
Year: {pub.get('year', 'Unknown')}
Venue: {pub.get('venue', 'Unknown')}
Citations: {pub.get('citations', 0)}
Tags: {', '.join(pub_tag_names) if pub_tag_names else 'research'}"""
            
            
            yield {
                "id": pub_id,
                "content": pub_content,
                "metadata": {
                    "doc_type": "publication",
                    "title": pub_title[:200],
                    "author": prof["name"],
                    "year": pub.get("year", ""),
                    "citations": str(pub.get("citations", 0)),
                    "tags": json.dumps(pub_tag_names),
                    "college": prof.get("college", "")
                }
            }


def load_data_to_vectorstore(config: CrawlConfig = RESTRICTED_CONFIG) -> Optional[VectorStore]:
    """Load crawled data into vector store with tags."""
    filepath = config.OUTPUT_FILE
    
    if not filepath.exists():
        console.print(f"[red]Data file not found: {filepath}[/]")
        console.print("[yellow]Run 'python main.py crawl' first[/]")
        return None
    
    with open(filepath) as f:
        data = json.load(f)
    
    store = VectorStore(config)
    store.initialize()
    store.clear()  # Start fresh
    
    BATCH_SIZE = 100
    batch = []
    count = 0
    
    with Timer("Processing data for vector store", use_rich=False):
        for doc in process_data_into_documents(data):
            batch.append(doc)
            if len(batch) >= BATCH_SIZE:
                 store.add_documents(batch)
                 count += len(batch)
                 batch = []
                 console.print(f"[dim]Processed {count} documents...[/]")
        
        # Add remaining
        if batch:
            store.add_documents(batch)
            count += len(batch)
            
    console.print(f"[bold blue]📦 Total {count} documents added to vector store.[/]")
    return store


def ingest_research_cards(config: CrawlConfig = RESTRICTED_CONFIG) -> Optional[VectorStore]:
    """Ingest distilled research cards into vector store."""
    cards_dir = config.BASE_DIR / "research_cards"
    if not cards_dir.exists():
        console.print(f"[yellow]No research cards found in {cards_dir}[/]")
        return None
        
    store = get_vector_store(config)
    store.initialize()
    
    cards = []
    for card_file in cards_dir.glob("*.json"):
        try:
            with open(card_file) as f:
                card = json.load(f)
                cards.append(card)
        except Exception:
            pass
            
    if cards:
        store.add_research_cards(cards)
        
    return store


# Global instance — Fix 5: thread-safe double-checked locking
import threading

_vector_store: Optional[VectorStore] = None
_vector_store_lock = threading.Lock()


def get_vector_store(config: CrawlConfig = RESTRICTED_CONFIG) -> VectorStore:
    """Get the global vector store instance (thread-safe)."""
    global _vector_store
    if _vector_store is None:
        with _vector_store_lock:
            if _vector_store is None:
                _vector_store = VectorStore(config)
    return _vector_store
