
"""
Test script for Hybrid Search (Vector + BM25) implementation.
"""
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config import RESTRICTED_CONFIG
from src.database.vector_store import get_vector_store, process_data_into_documents
from src.retrieval.hybrid_retriever import HybridRetriever

console = Console()

def run_test():
    console.print("[bold blue]🚀 Starting Hybrid Search Test...[/]")
    
    # 1. Load Data
    data_path = RESTRICTED_CONFIG.OUTPUT_FILE
    if not data_path.exists():
        console.print(f"[red]Error: Data file not found at {data_path}[/]")
        return
        
    with open(data_path, 'r') as f:
        data = json.load(f)
        
    # 2. Process Documents
    documents = process_data_into_documents(data)
    console.print(f"[green]Loaded {len(documents)} documents from {data_path.name}[/]")
    
    # 3. Initialize Vector Store
    # We assume vector store is already populated or we populate it now
    vs = get_vector_store(RESTRICTED_CONFIG)
    vs.initialize()
    if vs.collection.count() == 0:
        console.print("[yellow]Vector store empty, populating...[/]")
        vs.add_documents(documents)
    else:
        console.print(f"[green]Vector store has {vs.collection.count()} documents[/]")
        
    # 4. Initialize Hybrid Retriever
    retriever = HybridRetriever(vs, documents)
    
    # 5. Run Queries
    queries = [
        "Christopher Kanan",
        "multimodal learning",
        "artificial intelligence ethics",
        "dean of golisano college"
    ]
    
    for query in queries:
        console.print(f"\n[bold yellow]🔎 Query: '{query}'[/]")
        
        # Get results
        vector_results = retriever._search_vector(query, k=5)
        bm25_results = retriever._search_bm25(query, k=5)
        hybrid_results = retriever.hybrid_search(query, k=5)
        
        # Display comparison
        table = Table(title=f"Results for '{query}'")
        table.add_column("Rank", style="cyan", no_wrap=True)
        table.add_column("Vector (Chroma)", style="magenta")
        table.add_column("Keyword (BM25)", style="blue")
        table.add_column("Hybrid (RRF)", style="green")
        
        for i in range(5):
            v_doc = vector_results[i] if i < len(vector_results) else None
            b_doc = bm25_results[i] if i < len(bm25_results) else None
            h_doc = hybrid_results[i] if i < len(hybrid_results) else None
            
            v_str = f"{v_doc['metadata'].get('name') or v_doc['metadata'].get('title')} ({v_doc['distance']:.4f})" if v_doc else "-"
            b_str = f"{b_doc['metadata'].get('name') or b_doc['metadata'].get('title')} ({b_doc['score']:.4f})" if b_doc else "-"
            h_str = f"{h_doc['metadata'].get('name') or h_doc['metadata'].get('title')} (RRF: {h_doc.get('rrf_score', 0):.4f})" if h_doc else "-"
            
            table.add_row(str(i+1), v_str, b_str, h_str)
            
        console.print(table)
        
        # Print detailed hybrid matches for the first query to inspect content
        if query == queries[0]:
            console.print("\n[bold]Top Hybrid Match Details:[/]")
            top_match = hybrid_results[0]
            console.print(f"Title/Name: {top_match['metadata'].get('name') or top_match['metadata'].get('title')}")
            console.print(f"Type: {top_match['metadata'].get('doc_type')}")
            console.print(f"Ranks: Vector={top_match.get('vector_rank')}, BM25={top_match.get('bm25_rank')}")

if __name__ == "__main__":
    run_test()
