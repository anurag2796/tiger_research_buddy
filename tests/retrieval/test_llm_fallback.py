import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
"""
Test LLM fallback in EntityExtractor (Strategy 1).

Tests cases where lexical matching fails and LLM should kick in.
"""

import sys
sys.path.append('.')

import networkx as nx
import json
from networkx.readwrite import node_link_graph
from src.retrieval.entity_extraction import EntityExtractor
from rich.console import Console

console = Console()

def test_llm_fallback():
    # Load graph
    console.print("[cyan]Loading Graph...[/]")
    with open("data/tiger_brain.json", "r") as f:
        data = json.load(f)
    G = node_link_graph(data)
    
    # Initialize with LLM fallback enabled
    console.print("[cyan]Initializing EntityExtractor with LLM fallback...[/]")
    extractor = EntityExtractor(G, enable_llm_fallback=True, threshold=2)
    
    if extractor.llm_client:
        console.print("[green]✓ LLM client loaded successfully[/]")
    else:
        console.print("[red]✗ LLM fallback disabled (client not available)[/]")
        return
    
    # Test queries
    test_cases = [
        {
            "query": "Who studies CNNs at RIT?",  # Should trigger LLM ("CNNs" != "convolutional neural networks")
            "expected_trigger": True,
            "description": "Synonym test (CNNs)"
        },
        {
            "query": "vision research papers",  # Should trigger LLM (no exact match)
            "expected_trigger": True,
            "description": "Semantic inference (vision → computer vision)"
        },
        {
            "query": "Who works on Spiking Neural Networks?",  # Should NOT trigger (exact match)
            "expected_trigger": False,
            "description": "Exact match (should use lexical only)"
        },
        {
            "query": "deep learning faculty",  # Lexical should find "deep learning"
            "expected_trigger": False,
            "description": "Exact match with multiple entities"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        console.print(f"\n[bold yellow]Test {i}: {test['description']}[/]")
        console.print(f"Query: \"{test['query']}\"")
        
        # Extract entities
        entities = extractor.extract(test['query'])
        
        # Check results
        if entities:
            console.print(f"[green]✓ Found {len(entities)} entities:[/]")
            for e in entities:
                console.print(f"  - {e['label']} ({e['type']}) -> {e['id']}")
        else:
            console.print(f"[yellow]! No entities found (lexical may have failed, checking if LLM triggered...)[/]")
        
        # For queries expected to trigger LLM, check if we got results
        if test['expected_trigger'] and len(entities) == 0:
            console.print(f"[dim]  (LLM should have been triggered for this query)[/]")

if __name__ == "__main__":
    test_llm_fallback()
