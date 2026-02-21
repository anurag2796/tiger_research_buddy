import sys
from pathlib import Path
from rich.console import Console

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.vector_store import ingest_research_cards, RESTRICTED_CONFIG

console = Console()

def main():
    console.print("[bold blue]🚀 Starting Vector Store Ingestion[/]")
    store = ingest_research_cards(RESTRICTED_CONFIG)
    
    if store:
        stats = store.get_stats()
        console.print(f"[green]✓ Vector Store contains {stats['total_documents']} documents[/]")
        
        # Verify the digital test card is there
        results = store.search("digital", n_results=1, doc_type="research_card")
        if results:
            console.print(f"[green]✓ Found test card: {results[0]['id']}[/]")
        else:
            console.print(f"[red]✗ Could not find test card in vector store[/]")

if __name__ == "__main__":
    main()
