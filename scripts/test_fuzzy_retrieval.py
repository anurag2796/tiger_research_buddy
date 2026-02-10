import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from src.retrieval.hybrid_retriever import HybridRetriever
from src.database.vector_store import VectorStore
from rich.console import Console
from rich.table import Table

console = Console()

def test_fuzzy_retrieval():
    # Load knowledge graph
    graph_path = "data/tiger_brain.json"
    
    # Mock Vector Store (we just want the Entity Extractor part, which is in Retriever)
    class MockVectorStore:
        def search(self, *args, **kwargs): return []
        
    retriever = HybridRetriever(vector_db=MockVectorStore(), graph_path=graph_path)
    
    # Define Test Cases
    test_cases = [
        "Thomas Kinsman" ,      # Exact Match (Should Pass)
        "Kinsman",              # Last Name Only (Should Pass?)
        "Thoms Kinsman",        # Typo (Should Pass?)
        "Tom Kinsman",          # Alias/Nickname (Should Pass?)
        "Kimsman",              # Typo (Should Pass now)
        "Alexander Ororbia",    # Exact Match
        "Ororbia",              # Last Name Only
        "Orobia",               # Typo (Should Pass now)
    ]
    
    table = Table(title="Fuzzy Name Retrieval Test")
    table.add_column("Query", style="cyan")
    table.add_column("Extracted Entity", style="green")
    table.add_column("Match Type", style="yellow")
    table.add_column("Score", style="magenta")

    console.print("[bold]Running Entity Extraction Tests...[/]")
    
    # Access the internal extractor directly for lower-level diagnostics
    extractor = retriever.entity_extractor
    
    for query in test_cases:
        results = extractor.extract(query)
        
        if results:
            match_labels = []
            for r in results:
                score = r.get('score', 'N/A')
                match_labels.append(f"{r['label']} ({score})")
            
            table.add_row(query, "\n".join(match_labels), "Found", str(results[0].get('score', 'N/A')))
        else:
            table.add_row(query, "[red]No Match[/]", "Failed", "0")
            
    console.print(table)

if __name__ == "__main__":
    test_fuzzy_retrieval()
