import sys
sys.path.append('.')

import networkx as nx
import json
from networkx.readwrite import node_link_graph
from src.retrieval.entity_extraction import EntityExtractor
from rich.console import Console

console = Console()

path = "data/tiger_brain.json"

with open(path, 'r') as f:
    data = json.load(f)

G = node_link_graph(data)

extractor = EntityExtractor(G)
console.print(f"[green]Initialized EntityExtractor with {len(extractor.index)} entries[/]")

# Test query
query = "Who works on Spiking Neural Networks?"
console.print(f"\n[bold]Query:[/] {query}")

# Debug the matching logic
query_lower = query.lower()
console.print(f"Query lowercase: '{query_lower}'")

# Check if "spiking neural networks" is in the index
test_label = "spiking neural networks"
if test_label in extractor.index:
    console.print(f"[green]✓ '{test_label}' IS in index[/]")
    console.print(f"  Node ID: {extractor.index[test_label]}")
    
    # Test the matching condition
    padded_query = f" {query_lower} "
    padded_label = f" {test_label} "
    
    console.print(f"\nPadded query: '{padded_query}'")
    console.print(f"Padded label: '{padded_label}'")
    console.print(f"Match test: '{padded_label}' in '{padded_query}' = {padded_label in padded_query}")
else:
    console.print(f"[red]✗ '{test_label}' NOT in index[/]")

# Now run the actual extract
entities = extractor.extract(query)
console.print(f"\n[bold]Extracted Entities:[/]")
if entities:
    for e in entities:
        console.print(f"  - {e['label']} ({e['type']}) -> {e['id']}")
else:
    console.print("  [dim]No entities found[/]")
