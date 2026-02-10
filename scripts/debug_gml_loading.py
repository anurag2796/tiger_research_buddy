import networkx as nx
from rich.console import Console

console = Console()

path = "data/tiger_brain.gml"

console.print(f"[cyan]Testing nx.read_gml('{path}')...[/]")
try:
    G = nx.read_gml(path)
    console.print(f"Loaded {len(G.nodes)} nodes.")
    # Check first node
    first_node = list(G.nodes(data=True))[0]
    console.print(f"First Node: {first_node}")
except Exception as e:
    console.print(f"[red]Error:[/]: {e}")

console.print(f"\n[cyan]Testing nx.read_gml('{path}', label='id')...[/]")
try:
    G = nx.read_gml(path, label='id')
    console.print(f"Loaded {len(G.nodes)} nodes.")
    # Check first node
    first_node = list(G.nodes(data=True))[0]
    console.print(f"First Node: {first_node}")
except Exception as e:
    console.print(f"[red]Error:[/]: {e}")
