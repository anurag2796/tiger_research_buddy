import lancedb
import pandas as pd
from typing import List, Dict, Optional
from rich.console import Console
from ..chatbot.ollama_client import OllamaClient
from ..utils.config import DATA_DIR

console = Console()

class LanceManager:
    """
    Manages the LanceDB vector store for TigerStack 2.0.
    """
    
    def __init__(self, db_name: str = "tiger_vectors.lance"):
        self.db_path = DATA_DIR / "lancedb"
        self.db_path.mkdir(exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))
        self.table_name = "research_docs"
        
        # We use Nomic via Ollama for embeddings
        self.embedder = OllamaClient(model="nomic-embed-text")

    def initialize(self):
        """Create table if not exists."""
        if self.table_name not in self.db.table_names():
            # Define schema implicitly by creating a dummy table
            # Schema: vector (768), text, metadata (json)
            # For now, we'll let Lance Infer it from the first add
            pass
            
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Nomic (via Ollama)."""
        embeddings = []
        for text in texts:
            # clean newlines to avoid issues
            clean_text = text.replace("\n", " ")
            try:
                # Use raw ollama lib if possible for speed, or client wrapper
                # Client wrapper is safer for now
                import ollama
                resp = ollama.embeddings(model='nomic-embed-text', prompt=clean_text)
                embeddings.append(resp['embedding'])
            except Exception as e:
                console.print(f"[red]Embedding error: {e}[/]")
                # Return zero vector or skip? Skip is safer
                embeddings.append([0.0]*768) 
        return embeddings

    def add_documents(self, documents: List[Dict]):
        """
        Add documents to both Vector DB and Graph Index.
        documents structure:
        [
            {
                "content": "Full text...",
                "metadata": {"title": "...", "url": "...", "type": "professor"}
            }
        ]
        """
        console.print(f"[dim]Generating embeddings for {len(documents)} docs...[/]")
        
        # batch processing
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            texts = [d['content'] for d in batch]
            ids = [d.get('id', f"doc_{i+j}") for j, d in enumerate(batch)]
            
            vectors = self.embed_texts(texts)
            
            data = []
            for j, doc in enumerate(batch):
                data.append({
                    "vector": vectors[j],
                    "text": doc['content'],
                    "id": ids[j],
                    "metadata": doc['metadata'] 
                    # LanceDB handles nested dicts well or flatten it
                })
            
            # Create or Append
            if self.table_name in self.db.table_names():
                tbl = self.db.open_table(self.table_name)
                tbl.add(data)
            else:
                self.db.create_table(self.table_name, data)
                
            console.print(f"[green]✓ Indexed batch {i}-{i+len(batch)}[/]")

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Semantic search."""
        if self.table_name not in self.db.table_names():
            return []
            
        # Embed query
        query_vec = self.embed_texts([query])[0]
        
        tbl = self.db.open_table(self.table_name)
        results = tbl.search(query_vec).limit(limit).to_pandas()
        
        # Convert back to list of dicts
        return results.to_dict('records')
