import time
import sys
import os
import json
from rich.console import Console
from rich.table import Table

# Mock implementation for benchmark
# Real implementation would import from src.database or use ollama directly

console = Console()

TEST_SENTENCES = [
    "What are Professor Kinsman's research interests?",
    "Faculty working on computer vision and machine learning",
    "Deep learning for autonomous driving systems",
    "Who teaches data mining at RIT?",
    "Recent publications in reliable AI systems"
]

def benchmark_minilm():
    """Benchmark the current sentence-transformers model."""
    try:
        from sentence_transformers import SentenceTransformer
        console.print("[dim]Loading MiniLM...[/]")
        start_load = time.time()
        model = SentenceTransformer('all-MiniLM-L6-v2')
        load_time = time.time() - start_load
        
        start_infer = time.time()
        embeddings = model.encode(TEST_SENTENCES)
        infer_time = time.time() - start_infer
        
        return {
            "model": "all-MiniLM-L6-v2",
            "load_time": load_time,
            "infer_time": infer_time,
            "avg_latency": (infer_time / len(TEST_SENTENCES)) * 1000,
            "dims": len(embeddings[0])
        }
    except ImportError:
        console.print("[red]sentence-transformers not installed[/]")
        return None

def benchmark_nomic():
    """Benchmark Nomic Embed Text via Ollama."""
    try:
        import ollama
        console.print("[dim]Loading Nomic (via Ollama)...[/]")
        
        # Check if model exists, pull if not
        try:
            ollama.show('nomic-embed-text')
        except:
            console.print("[yellow]Pulling nomic-embed-text...[/]")
            ollama.pull('nomic-embed-text')

        start_infer = time.time()
        # Process one by one for latency test
        for text in TEST_SENTENCES:
            ollama.embeddings(model='nomic-embed-text', prompt=text)
        infer_time = time.time() - start_infer
        
        # Get dimensions
        sample = ollama.embeddings(model='nomic-embed-text', prompt="test")
        dims = len(sample['embedding'])

        return {
            "model": "nomic-embed-text",
            "load_time": 0, # Service already running
            "infer_time": infer_time,
            "avg_latency": (infer_time / len(TEST_SENTENCES)) * 1000,
            "dims": dims
        }
    except Exception as e:
        console.print(f"[red]Nomic benchmark failed: {e}[/]")
        return None

def main():
    console.print("[bold blue]🧪 Embedding Benchmark[/]")
    
    results = []
    
    # Run MiniLM
    res_mini = benchmark_minilm()
    if res_mini: results.append(res_mini)
    
    # Run Nomic
    res_nomic = benchmark_nomic()
    if res_nomic: results.append(res_nomic)
    
    # Display Table
    table = Table(title="Embedding Performance Comparison")
    table.add_column("Model", style="cyan")
    table.add_column("Dimensions", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("Notes")
    
    for r in results:
        notes = "Local Library" if "MiniLM" in r['model'] else "Ollama API"
        table.add_row(
            r['model'],
            str(r['dims']),
            f"{r['avg_latency']:.2f}",
            notes
        )
        
    console.print(table)
    
    # Quality Analysis Suggestion
    console.print("\n[bold]Semantic Quality Note:[/]")
    console.print("MiniLM (384d) is fast but limited context (512 tokens).")
    console.print("Nomic (768d) supports 8192 context window and MTEB leaderboard top-tier.")

if __name__ == "__main__":
    main()
