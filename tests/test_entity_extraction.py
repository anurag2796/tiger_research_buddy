import sys
import os
sys.path.append(os.getcwd())

import networkx as nx
from src.retrieval.entity_extraction import EntityExtractor
from rich.console import Console

console = Console()

def test_extractor():
    # Load the real graph (now in JSON format)
    console.print("[cyan]Loading Graph...[/]")
    import json
    from networkx.readwrite import node_link_graph
    
    with open("data/tiger_brain.json", "r") as f:
        data = json.load(f)
    G = node_link_graph(data)
    
    extractor = EntityExtractor(G)
    console.print(f"[green]Index built with {len(extractor.index)} entries.[/]")
    
    # Use ACTUAL keywords from research cards
    test_queries = [
        "Who works on Spiking Neural Networks?",
        "Tell me about Christopher Kanan",
        "Does anyone study Computer Vision?",
        "What research involves Deep Learning?"
    ]
    
    for q in test_queries:
        console.print(f"\n[bold]Query:[/] {q}")
        entities = extractor.extract(q)
        if entities:
            for e in entities:
                console.print(f"  - [yellow]{e['label']}[/] ({e['type']}) -> {e['id']}")
        else:
            console.print(f"  [dim]No entities found[/]")

if __name__ == "__main__":
    test_extractor()
