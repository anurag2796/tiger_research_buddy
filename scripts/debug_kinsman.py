import json
import networkx as nx
from networkx.readwrite import node_link_graph
from rich.console import Console

console = Console()

def inspect_kinsman():
    # Load Graph
    graph_path = "data/tiger_brain.json"
    console.print(f"Loading Graph from {graph_path}...")
    with open(graph_path, "r") as f:
        data = json.load(f)
    G = node_link_graph(data)
    
    console.print(f"Graph loaded: {len(G.nodes)} nodes")
    
    # Search for Kinsman
    found = False
    for n, data in G.nodes(data=True):
        label = data.get('label', '').lower()
        name = data.get('name', '').lower()
        
        if 'kinsman' in label or 'kinsman' in name:
            found = True
            console.print(f"Node: {n}")
            console.print(f"  Type: {data.get('type')}")
            console.print(f"  Name: {data.get('name')}")
            console.print(f"  Label: {data.get('label')}")
            console.print(f"  Bio: {data.get('bio', 'N/A')}")
            console.print(f"  Dept: {data.get('department', 'N/A')}")
            
            # Print neighbors
            neighbors = list(G.neighbors(n))
            console.print(f"  Neighbors ({len(neighbors)}):")
            for nb in neighbors[:5]:
                nb_data = G.nodes[nb]
                console.print(f"    - {nb_data.get('label', nb)} ({nb_data.get('type')})")
            console.print("-" * 20)

    if not found:
        console.print("[red]No node found for 'Kinsman'[/]")

if __name__ == "__main__":
    inspect_kinsman()
