"""Vector store using ChromaDB for semantic search."""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..utils.config import CHROMA_DIR, DATA_DIR, COLLECTION_NAME, EMBEDDING_MODEL

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
    """Lazy load embedding function."""
    global _embedding_function
    if _embedding_function is None:
        from chromadb.utils import embedding_functions
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _embedding_function


class VectorStore:
    """Vector database for semantic search over research data."""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the vector store."""
        if self._initialized:
            return
            
        console.print("[bold blue]📦 Initializing vector store...[/]")
        
        chromadb = _get_chromadb()
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
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
            self.client.delete_collection(COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=_get_embedding_function()
            )
            console.print("[yellow]Cleared vector store[/]")
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        if not self._initialized:
            self.initialize()
        
        return {
            "total_documents": self.collection.count(),
            "collection_name": COLLECTION_NAME
        }


def load_data_to_vectorstore(data_file: str = "rit_data.json") -> VectorStore:
    """Load crawled data into vector store with tags."""
    from ..utils.tag_generator import generate_tags_for_professor, generate_tags_for_research_area, generate_tags_for_publication
    
    filepath = DATA_DIR / data_file
    
    if not filepath.exists():
        console.print(f"[red]Data file not found: {filepath}[/]")
        console.print("[yellow]Run 'python main.py crawl' first[/]")
        return None
    
    with open(filepath) as f:
        data = json.load(f)
    
    store = VectorStore()
    store.initialize()
    store.clear()  # Start fresh
    
    documents = []
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
        
        documents.append({
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "research_area",
                "name": area["name"],
                "url": area.get("url", ""),
                "college": area.get("college", ""),
                "tags": json.dumps(tag_names)
            }
        })
    
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
        bio = prof.get("bio", "")[:500] if prof.get("bio") else ""
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
Recent Publications: {', '.join(p.get('title', '')[:100] for p in pubs[:5]) if pubs else 'Not available'}
Profile URL: {prof.get('profile_url', '')}
College: {prof.get('college', '')}"""
        
        documents.append({
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "professor",
                "name": prof["name"],
                "title": prof.get("title", ""),
                "url": prof.get("profile_url", ""),
                "tags": json.dumps(tag_names),
                "citations": str(citations),
                "h_index": str(h_index),
                "college": prof.get("college", "")
            }
        })
        
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
            
            documents.append({
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
            })
    
    console.print(f"[bold blue]📦 Adding {len(documents)} documents to vector store...[/]")
    store.add_documents(documents)
    return store



# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
