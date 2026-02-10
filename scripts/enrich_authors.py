import json
import networkx as nx
from networkx.readwrite import node_link_graph, node_link_data
from rich.console import Console
from rich.progress import track
from src.chatbot.ollama_client import get_ollama_client

console = Console()

def enrich_authors():
    """
    Uses local LLM to enrich author nodes that have missing bios or incomplete names.
    """
    graph_path = "data/tiger_brain.json"
    
    console.print(f"[cyan]Loading Graph from {graph_path}...[/]")
    with open(graph_path, "r") as f:
        data = json.load(f)
    G = node_link_graph(data)
    
    client = get_ollama_client()
    
    # Identify candidates: Faculty/Author nodes with no bio or short names
    candidates = []
    for n, d in G.nodes(data=True):
        if d.get('type') in ['faculty', 'author']:
            # Check for missing bio or comma-based name (indicating raw extraction)
            name = d.get('name', d.get('label', ''))
            bio = d.get('bio', '')
            
            if ',' in name or len(bio) < 10:
                candidates.append(n)
    
    console.print(f"[yellow]Found {len(candidates)} candidates for enrichment.[/]")
    
    # Process a subset for PoC (e.g. Kanan)
    # in real run, we'd do all
    target_candidates = [n for n in candidates if 'Kanan' in G.nodes[n].get('label', '') or 'Kafl' in G.nodes[n].get('label', '')]
    
    if not target_candidates:
        console.print("[red]No targets found matching filter (Kanan/Kafl).[/]")
        return

    for n in track(target_candidates, description="Enriching Authors..."):
        node = G.nodes[n]
        original_name = node.get('label', '')
        
        # 1. Gather context from authored papers
        context_text = ""
        neighbors = list(G.neighbors(n)) + list(G.predecessors(n)) if G.is_directed() else list(G.neighbors(n))
        
        papers = []
        for nb in neighbors:
            if G.nodes[nb].get('type') == 'paper':
                papers.append(G.nodes[nb].get('label', ''))
        
        if not papers:
            console.print(f"[dim]Skipping {original_name} (No papers found)[/]")
            continue
            
        context_text = f"Author Name: {original_name}\nAuthored Papers: {', '.join(papers[:3])}"
        
        # 2. Ask LLM to infer/standardize
        prompt = f"""
        You are a Data Cleaning assistant.
        Given an author name and their papers, infer their likely Full Name and a short professional bio.
        
        Input:
        {context_text}
        
        Format output as JSON:
        {{
            "full_name": "First Last",
            "bio": "Professor of X working on Y...",
            "affiliation": "Likely Department/University"
        }}
        """
        
        try:
            response = client.generate(prompt)
            # clean json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                info = json.loads(json_str)
                
                # Update Node
                node['name'] = info.get('full_name', original_name)
                # Keep original label to not break links, or update label if using IDs?
                # Best to add 'canonical_name'
                node['canonical_name'] = info.get('full_name')
                node['bio'] = info.get('bio', '')
                node['department'] = info.get('affiliation', '')
                node['enriched'] = True
                
                console.print(f"[green]Enriched {original_name} -> {node['name']}[/]")
            
        except Exception as e:
            console.print(f"[red]Failed to enrich {original_name}: {e}[/]")

    # Save Graph
    console.print(f"[cyan]Saving enriched graph...[/]")
    with open(graph_path, "w") as f:
        json.dump(node_link_data(G), f, indent=2)
    console.print("[green]Done![/]")

if __name__ == "__main__":
    enrich_authors()
