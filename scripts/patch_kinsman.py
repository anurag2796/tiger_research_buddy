import json
import networkx as nx
from networkx.readwrite import node_link_graph, node_link_data
from rich.console import Console

console = Console()

def patch_kinsman():
    graph_path = "data/tiger_brain.json"
    
    console.print(f"Loading Graph from {graph_path}...")
    with open(graph_path, "r") as f:
        data = json.load(f)
    G = node_link_graph(data)
    
    # 1. Create Node
    node_id = "faculty_kinsman"
    if node_id in G.nodes:
        console.print("[yellow]Node faculty_kinsman already exists.[/]")
    else:
        G.add_node(node_id, 
                   type="faculty", 
                   name="Thomas Kinsman",
                   label="Kinsman, Thomas",
                   bio="Professor at Computer Science Department, RIT. Works on Computer Vision and Graphics.",
                   department="Computer Science",
                   title="Professor")
        console.print(f"[green]Created node {node_id}[/]")

    # 2. Link to Papers
    # Iterate research cards to find matches
    import glob
    card_files = glob.glob("data/research_cards/*.json")
    linked_count = 0
    
    console.print(f"Scanning {len(card_files)} research cards...")
    
    for card_path in card_files:
        try:
            with open(card_path, "r") as f:
                card = json.load(f)
            
            source = card.get("source_file", "").lower()
            if "kinsman" in source:
                title = card.get("Title", "") # Note: Title case key in some cards? check
                if not title:
                     title = card.get("title", "")
                
                # Find node with matching label
                # This is O(N) per card, but N=48k, scanning 5 files is fast.
                target_node = None
                for n, d in G.nodes(data=True):
                    if d.get('type') == 'paper' and d.get('label') == title:
                        target_node = n
                        break
                
                if target_node:
                    G.add_edge(node_id, target_node, type="AUTHORED", weight=1.0)
                    console.print(f"Linked to paper: {title}")
                    linked_count += 1
                else:
                    console.print(f"[dim]Could not find node for paper: {title}[/]")
                    
        except Exception as e:
            console.print(f"[red]Error processing {card_path}: {e}[/]")

    # 3. Link to Concepts
    
    # 3. Link to Concepts
    # Link to "computer_science" if exists, or just generic
    if "computer_science" in G.nodes:
        G.add_edge(node_id, "computer_science", type="INTERESTED_IN", weight=0.5)
        
    console.print(f"Linked to {linked_count} papers.")
    
    # Save
    console.print(f"Saving graph to {graph_path}...")
    with open(graph_path, "w") as f:
        json.dump(node_link_data(G), f, indent=2)
    console.print("[green]Patched Successfully![/]")

if __name__ == "__main__":
    patch_kinsman()
