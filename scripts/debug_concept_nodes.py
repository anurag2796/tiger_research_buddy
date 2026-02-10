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

# Find a concept node for "spiking neural networks"
if "spiking_neural_networks" in G.nodes:
    n = "spiking_neural_networks"
    d = G.nodes[n]
    console.print(f"\n[yellow]Found concept node:[/]")
    console.print(f"ID: {n}")
    console.print(f"Data: {d}")
else:
    console.print("[red]spiking_neural_networks not found![/]")
    
    # Find ANY concept node
    for n, d in G.nodes(data=True):
        if d.get('type') == 'concept':
            console.print(f"\n[yellow]Found a concept node:[/]")
            console.print(f"ID: {n}")
            console.print(f"Data: {d}")
            break
