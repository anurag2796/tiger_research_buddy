import sys
import os
from rich.console import Console
from rich.panel import Panel

# Add project root to path
sys.path.append(os.getcwd())

from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.synthesizer import ResponseSynthesizer
from src.database.lance_manager import LanceManager

console = Console()

def main():
    console.print(Panel.fit("[bold cyan]Welcome to TigerStack 2.0 Chat[/]", border_style="cyan"))
    
    # Initialize components
    console.print("[dim]Initializing Retrieval System...[/]")
    db_manager = LanceManager()
    
    # We need the vector DB instance from LanceManager
    # Assuming LanceManager has a method to get the vector table/index
    # For now, let's look at how HybridRetriever is initialized.
    # It expects `vector_db` and `graph_path`.
    
    # Wait, LanceManager manages the DB but HybridRetriever takes a vector_db object?
    # Let's check HybridRetriever's __init__ signature.
    # __init__(self, vector_db, graph_path: str)
    
    # And LanceManager usually exposes the table or search method.
    # Let's assume LanceManager IS the vector_db interface or has one.
    # Actually, looking at previous code, HybridRetriever might expect a specific VectorStore class.
    # Let me check LanceManager code quickly.
    
    # Placeholder for now: treating db_manager as vector_db
    retriever = HybridRetriever(
        vector_db=db_manager, 
        graph_path="data/tiger_brain.json"
    )
    
    synthesizer = ResponseSynthesizer()
    
    console.print("[bold green]System Ready![/]\n")
    
    while True:
        try:
            query = console.input("[bold yellow]You > [/]")
            if query.lower() in ('exit', 'quit'):
                break
            
            with console.status("[bold green]Thinking...[/]"):
                # 1. Retrieve
                results = retriever.retrieve(query, limit=5)
                
                # 2. Synthesize
                response = synthesizer.synthesize(query, results)
            
            console.print(f"\n[bold cyan]TigerBrain >[/] {response}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

if __name__ == "__main__":
    main()
