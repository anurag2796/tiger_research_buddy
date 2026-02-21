
import time
import sys
import os
from rich.console import Console

# Add src to path
sys.path.append(os.getcwd())

from src.database import get_vector_store
from src.chatbot.ollama_client import get_ollama_client
from src.utils.db_logger import PerformanceTimer
from src.chatbot.query_engine import QueryEngine

console = Console()

def simulate_activity():
    console.print("[bold blue]🚀 Starting User Activity Simulation...[/]")
    
    queries = [
        "Who works on deep learning?",
        "Tell me about sustainable energy research.",
        "Combine AI with healthcare.",
        "What are the research areas of Department of CS?"
    ]
    
    # Initialize components
    with PerformanceTimer("Initialization"):
        store = get_vector_store()
        store.initialize()
        client = get_ollama_client()
        client.initialize()
        query_engine = QueryEngine()

    for i, query in enumerate(queries, 1):
        console.print(f"\n[bold yellow]Query {i}: {query}[/]")
        
        # 1. Query Expansion
        with PerformanceTimer("Query Expansion", meta={"query": query}):
            expanded_query = query_engine.expand_query(query)
            console.print(f"[dim]Expanded: {expanded_query}[/]")

        # 2. Vector Search
        with PerformanceTimer("Vector Search", meta={"query": expanded_query}):
            results = store.search(expanded_query, n_results=10)
            console.print(f"[dim]Found {len(results)} docs[/]")

        # 3. Graph Insights
        with PerformanceTimer("Graph Insights", meta={"query": query}):
            insights = query_engine.get_graph_insights(query)
            console.print(f"[dim]Insights found: {list(insights.keys())}[/]")
            
            enrichment = query_engine.enrich_context(query, results)

        # 4. LLM Generation
        context = "\n".join([r['content'] for r in results])
        if enrichment:
            context += f"\n\nGraph Insights:\n{enrichment}"
            
        system_prompt = "You are a helpful research assistant."
        
        with PerformanceTimer("LLM Response Generation", meta={"query": query}):
            # Non-streaming for simulation to catch full time
            response = client.generate(query, context=context, system_prompt=system_prompt)
            console.print(f"[green]Response generated ({len(response)} chars)[/]")

    console.print("\n[bold green]✅ Simulation Complete![/]")

if __name__ == "__main__":
    simulate_activity()
