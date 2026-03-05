import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
"""Test the graph-enriched query engine integration."""

from rich.console import Console
from src.chatbot.query_engine import QueryEngine

console = Console()


def test_query_engine():
    """Test the graph-enhanced query engine."""
    console.print("[bold cyan]🧪 Testing Graph-Enhanced Query Engine[/]\n")
    
    engine = QueryEngine()
    
    # Test queries
    test_queries = [
        "Who works on machine learning at RIT",
        "Tell me about Travis Desell's research",
        "Find faculty working on AI and cybersecurity",
        "Who are the leading researchers in natural language processing?"
    ]
    
    for query in test_queries:
        console.print(f"\n[bold]Query:[/] {query}")
        console.print("[dim]─" * 60 + "[/]")
        
        # Get graph insights
        insights = engine.get_graph_insights(query)
        
        if insights:
            console.print(f"[green]✓ Found {len(insights)} types of insights:[/]")
            
            for key, value in insights.items():
                console.print(f"\n  [cyan]{key}:[/]")
                if isinstance(value, list):
                    for item in value[:3]:  # Show first 3
                        if isinstance(item, dict):
                            console.print(f"    - {item}")
                        else:
                            console.print(f"    - {item}")
                else:
                    console.print(f"    {value}")
        else:
            console.print("[yellow]No graph insights found[/]")
        
        # Test enrichment (mock results)
        mock_results = [{"content": "Sample document content", "metadata": {}}]
        enrichment = engine.enrich_context(query, mock_results)
        
        if enrichment:
            console.print(f"\n[bold green]✓ Graph Enrichment Generated:[/]")
            console.print(f"[dim]{enrichment[:300]}...[/]")
        else:
            console.print("[dim]No enrichment generated[/]")


def main():
    console.print("[bold magenta]🐅 TigerResearchBuddy Query Engine Test[/]\n")
    
    try:
        test_query_engine()
        console.print("\n[bold green]✓ Tests completed![/]")
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
