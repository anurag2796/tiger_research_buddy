from pyvis.network import Network
import networkx as nx
from pathlib import Path
from rich.console import Console

console = Console()

class GraphVisualizer:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.input_path = self.data_dir / "tiger_brain_refined.gml"
        # Fallback to raw if refined doesn't exist? No, user wants sophisticated.
        if not self.input_path.exists():
            self.input_path = self.data_dir / "tiger_brain.gml"
            
        self.output_path = self.data_dir / "tiger_brain_viz.html"

    def visualize(self):
        if not self.input_path.exists():
            console.print(f"[red]Input Graph not found![/]")
            return

        console.print(f"[cyan]Loading {self.input_path}...[/]")
        G = nx.read_gml(self.input_path)
        
        # Configure PyVis
        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", notebook=False)
        
        # Color Coding Scheme
        # Faculty: Blue
        # Paper: Green
        # Concept: Orange
        # Topic Cluster: Purple
        
        colors = {
            "faculty": "#57C7FF",
            "paper": "#5AF78E",
            "concept": "#FF9F1C",
            "topic_cluster": "#BF5AF2",
            "unknown": "#888888"
        }

        # Add Nodes with Styles
        console.print("[cyan]Styling Nodes...[/]")
        for n, d in G.nodes(data=True):
            node_type = d.get("type", "unknown")
            color = colors.get(node_type, colors["unknown"])
            
            # Size
            size = 10
            if node_type == "faculty": size = 20
            elif node_type == "topic_cluster": size = 30
            elif node_type == "paper": size = 15
            
            # Title (Tooltip)
            title = d.get("label", n)
            if node_type == "faculty":
                title += f"\nDept: {d.get('dept', '')}\nInterests: {d.get('research_interests', '')}"
            
            net.add_node(n, label=d.get("label", n), title=title, color=color, size=size)

        # Add Edges
        console.print("[cyan]Adding Edges...[/]")
        for u, v, d in G.edges(data=True):
            # Filtering visual clutter? Maybe later.
            net.add_edge(u, v)

        # Physics Options for better layout
        net.barnes_hut()
        
        # Save
        console.print(f"[green]Rendering to {self.output_path}...[/]")
        net.save_graph(str(self.output_path))
        console.print(f"[bold green]✨ Visualization Ready![/]")

if __name__ == "__main__":
    viz = GraphVisualizer()
    viz.visualize()
    
