import json
import networkx as nx
from networkx.readwrite import node_link_graph
from rich.console import Console

console = Console()

def inspect():
    with open("data/tiger_brain.json", "r") as f:
        data = json.load(f)
    G = node_link_graph(data)
    
    console.print(f"Graph loaded: {G.number_of_nodes()} nodes")
    
    # Search for nodes with "Kanan" in label or name
    for n, data in G.nodes(data=True):
        label = data.get('label', '')
        name = data.get('name', '')
        
        if 'kanan' in str(label).lower() or 'kanan' in str(name).lower():
            console.print(f"Node: {n}")
            console.print(f"  Type: {data.get('type')}")
            console.print(f"  Name: {name}")
            console.print(f"  Label: {label}")
            console.print(f"  Bio: {data.get('bio', 'N/A')}")
            console.print(f"  Dept: {data.get('department', 'N/A')}")
            console.print("-" * 20)

if __name__ == "__main__":
    inspect()
