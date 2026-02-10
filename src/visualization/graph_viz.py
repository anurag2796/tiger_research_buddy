import networkx as nx
from pyvis.network import Network
from rich.console import Console
from pathlib import Path
from ..utils.config import DATA_DIR

console = Console()

class GraphVisualizer:
    """
    Visualizes the RIT Site Graph and Knowledge Graph using PyVis.
    Generates interactive HTML files.
    """

    def __init__(self):
        self.output_dir = DATA_DIR / "viz"
        self.output_dir.mkdir(exist_ok=True)
        self.site_graph_path = DATA_DIR / "site_graph.gml"

    def visualize_site_graph(self, limit: int = 1000):
        """
        Visualizes the crawling graph.
        Limit nodes to prevent browser crash on huge graphs.
        """
        if not self.site_graph_path.exists():
            console.print("[red]No site graph found. Run 'crawl-smart' first.[/]")
            return

        console.print("[cyan]Loading Site Graph...[/]")
        try:
            G = nx.read_gml(self.site_graph_path)
            console.print(f"[dim]Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges[/]")
        except Exception as e:
            console.print(f"[red]Error loading graph: {e}[/]")
            return

        # Create PyVis Network
        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", select_menu=True)
        
        # Optimize for physics
        net.barnes_hut()
        
        # Color nodes by type/degree
        # Faculty profiles usually have 'profile' in URL or high degree?
        # For now, let's just color by degree (connectivity)
        
        # Subgraph if too large
        if G.number_of_nodes() > limit:
            console.print(f"[yellow]Graph too large ({G.number_of_nodes()} nodes). showing top {limit} by connectivity.[/]")
            degrees = dict(G.degree())
            top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:limit]
            G = G.subgraph(top_nodes)

        console.print("[cyan]Building interactive visualization...[/]")
        
        for node in G.nodes():
            # Simple heuristic: URLs with 'profile' or human names are likely relevant
            # In site_graph.gml, nodes are URLs
            label = str(node).split("/")[-1] # Short label
            
            # Color logic
            color = "#97c2fc" # Default blue
            if "directory" in str(node):
                color = "#ffb347" # Orange for directory pages
                
            title = str(node) # Full URL on hover
            
            net.add_node(node, label=label, title=title, color=color)

        for edge in G.edges():
            net.add_edge(edge[0], edge[1], color="#rgba(255,255,255,0.2)")

        # Save
        output_file = self.output_dir / "site_map.html"
        net.save_graph(str(output_file))
        
        console.print(f"[bold green]✅ Visualization saved to {output_file}[/]")
        console.print(f"[dim]Open this file in your browser to explore the RIT Spider Map.[/]")
