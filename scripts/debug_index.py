import networkx as nx
import json
from networkx.readwrite import node_link_graph
from rich.console import Console

console = Console()

path = "data/tiger_brain.json"

with open(path, 'r') as f:
    data = json.load(f)

G = node_link_graph(data)

console.print(f"[cyan]Loaded {len(G.nodes)} nodes[/]")

# Simulate _build_index logic
index = {}
for node, data in G.nodes(data=True):
    # Priority 1: Try 'name' attribute (used for concepts)
    label = data.get('name', '')
    
    # Priority 2: Try 'label' attribute
    if not label:
        label = data.get('label', '')
    
    # Fallback: If no label, use the node ID itself (if it's a string)
    if not label and isinstance(node, str):
        label = node
        
    if label:
        index[str(label).lower()] = node

console.print(f"[green]Index built with {len(index)} entries[/]")

# Test if "spiking neural networks" is in index
test_key = "spiking neural networks"
if test_key in index:
    console.print(f"\n[bold green]✓ Found '{test_key}' in index![/]")
    console.print(f"  Maps to node: {index[test_key]}")
else:
    console.print(f"\n[bold red]✗ '{test_key}' NOT in index[/]")
    
    # Show first 10 concept-related keys
    console.print("\n[yellow]First 10 keys containing 'spiking':[/]")
    spike_keys = [k for k in index.keys() if 'spiking' in k]
    for k in spike_keys[:10]:
        console.print(f"  - {k} -> {index[k]}")
