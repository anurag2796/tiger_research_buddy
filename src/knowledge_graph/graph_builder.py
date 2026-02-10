import json
import networkx as nx
from pathlib import Path
from rich.console import Console
from rich.progress import track
from src.knowledge_graph.entity_resolver import EntityResolver

console = Console()

class GraphBuilder:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.site_graph_path = self.data_dir / "site_graph.gml"
        self.cards_dir = self.data_dir / "research_cards"
        self.output_path = self.data_dir / "tiger_brain.gml"
        self.graph = nx.Graph()
        self.entity_resolver = EntityResolver(self.data_dir)

    def load_site_graph(self):
        """Load the structural skeleton from SmartCrawler."""
        if not self.site_graph_path.exists():
            console.print(f"[red]Site Graph not found at {self.site_graph_path}![/]")
            return
        
        console.print(f"[cyan]Loading Site Graph...[/]")
        # Site graph is still in GML format (from scraper)
        self.graph = nx.read_gml(self.site_graph_path)
        console.print(f"[green]Loaded {self.graph.number_of_nodes()} nodes from Site Graph.[/]")

    def load_faculty_data(self):
        """Enrich graph with Faculty nodes from RIT Data JSON."""
        json_path = self.data_dir / "rit_data_v2.json"
        
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            faculty_list = data.get("faculty", [])
            console.print(f"[cyan]Hydrating {len(faculty_list)} Faculty Nodes...[/]")
            
            for f in faculty_list:
                name = f.get("name")
                if name:
                    # Create/Update Node
                    # Store rich metadata
                    self.graph.add_node(
                        name, 
                        type="faculty", 
                        title=f.get("title", ""),
                        dept=f.get("department", ""),
                        email=f.get("email", ""),
                        url=f.get("url", "")
                    )
                    
        except Exception as e:
            console.print(f"[red]Failed to load faculty data: {e}[/]")

    def merge_research_cards(self):
        """Integrate semantic knowledge from Research Cards."""
        json_files = list(self.cards_dir.glob("*.json"))
        if not json_files:
            console.print("[red]No Research Cards found![/]")
            return

        # Cache faculty names for fuzzy matching
        faculty_nodes = [
            str(n) for n, d in self.graph.nodes(data=True) 
            if d.get("type") == "faculty" and n
        ]
        console.print(f"[cyan]Integrating {len(json_files)} Research Cards with {len(faculty_nodes)} Faculty nodes...[/]")

        for json_file in track(json_files, description="Merging Knowledge..."):
            try:
                with open(json_file, "r") as f:
                    card = json.load(f)
                
                paper_title = card.get("title", "Unknown Paper")
                paper_id = f"paper_{paper_title.lower().replace(' ', '_')}"[:50] # Truncate ID
                
                # 1. Add Paper Node
                self.graph.add_node(paper_id, type="paper", label=paper_title, year=card.get("year", ""))

                # 2. Link Authors (Faculty)
                authors = card.get("authors", [])
                normalized_authors = []
                for a in authors:
                    if isinstance(a, str):
                        normalized_authors.append(a)
                    elif isinstance(a, dict) and "name" in a:
                        normalized_authors.append(a["name"])

                # Resolve authors to canonical IDs
                for author_name in normalized_authors:
                    # Context for resolution
                    affiliation = card.get("institution", "")
                    coauthors = [a for a in normalized_authors if a != author_name]
                    
                    # Resolve!
                    canonical_id = self.entity_resolver.resolve_author(
                        author_name, affiliation, coauthors
                    )
                    
                    canonical_name = self.entity_resolver.get_canonical_name(canonical_id)
                    
                    # Ensure Canonical Node Exists in Graph
                    if not self.graph.has_node(canonical_id):
                        self.graph.add_node(
                            canonical_id, 
                            type="faculty", 
                            label=canonical_name,
                            # We can try to hydrate more info from existing site graph nodes if they match
                        )
                    
                    # Link Paper -> Canonical Author
                    self.graph.add_edge(canonical_id, paper_id, type="AUTHORED", weight=1.0)

                # 3. Add Concepts & Relations
                kg = card.get("knowledge_graph", {})
                
                # TigerCard 2.0 has 'nodes' and 'edges'. Old schema had 'entities' and 'relations'.
                nodes = kg.get("nodes", kg.get("entities", []))
                edges = kg.get("edges", kg.get("relations", []))
                
                # Add Concept Nodes from structured KG
                for node in nodes:
                    concept_id = node.get("id")
                    concept_label = node.get("label", node.get("name")) # Handle both
                    concept_type = node.get("type", "concept")
                    
                    if concept_id:
                        if not self.graph.has_node(concept_id):
                            self.graph.add_node(concept_id, type="concept", label=concept_label, concept_type=concept_type)
                        
                        # Link Paper -> Concept
                        self.graph.add_edge(paper_id, concept_id, type="MENTIONS", weight=1.0)
                
                # Fallback: Use keywords as concepts if KG is sparse
                # This ensures coverage for cards where DeepDistiller didn't extract entities
                keywords = card.get("keywords", [])
                for keyword in keywords:
                    if not keyword or len(keyword) < 3:  # Skip empty/short keywords
                        continue
                    
                    # Use normalized keyword as ID, original as display name
                    concept_id = keyword.lower().replace(" ", "_")
                    
                    if not self.graph.has_node(concept_id):
                        # Use 'name' instead of 'label' to avoid GML conflicts
                        self.graph.add_node(concept_id, type="concept", name=keyword, concept_type="keyword")
                    
                    # Link Paper -> Keyword Concept
                    self.graph.add_edge(paper_id, concept_id, type="HAS_TOPIC", weight=0.8)

                # Add Concept-Concept Relations (from the card)
                for edge in edges:
                    src = edge.get("source")
                    tgt = edge.get("target")
                    rel_type = edge.get("relation", edge.get("type", "RELATED_TO")) # Handle both
                    
                    if src and tgt and self.graph.has_node(src) and self.graph.has_node(tgt):
                        self.graph.add_edge(src, tgt, type=rel_type, weight=0.5)

            except Exception as e:
                console.print(f"[yellow]Skipping {json_file.name}: {e}[/]")

    def sanitize_graph(self):
        """Ensure all attributes are GML-compatible (no None values)."""
        # Fix Nodes
        for n in list(self.graph.nodes()):
            # Ensure canonical ID is preserved as attribute
            self.graph.nodes[n]['canonical_id'] = str(n)
            
            attrs = self.graph.nodes[n]
            for k, v in list(attrs.items()):
                if v is None:
                    self.graph.nodes[n][k] = ""
                elif not isinstance(v, (str, int, float, bool)):
                    self.graph.nodes[n][k] = str(v)
        
        # Fix Edges
        for u, v in list(self.graph.edges()):
            attrs = self.graph.edges[u, v]
            for k, val in list(attrs.items()):
                if val is None:
                    self.graph.edges[u, v][k] = ""
                elif not isinstance(val, (str, int, float, bool)):
                    self.graph.edges[u, v][k] = str(val)

    def export(self):
        """Save the fused graph."""
        self.sanitize_graph()
        try:
            # Use JSON format instead of GML to preserve all node attributes
            import json
            from networkx.readwrite import node_link_data
            
            # Change output path from .gml to .json
            json_path = self.output_path.with_suffix('.json')
            
            data = node_link_data(self.graph)
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            console.print(f"\n[bold green]🐅 TigerBrain Built Successfully![/]")
            console.print(f"Stats: {self.graph.number_of_nodes()} Nodes | {self.graph.number_of_edges()} Edges")
            console.print(f"Saved to: {json_path}")
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/]")

if __name__ == "__main__":
    builder = GraphBuilder()
    builder.load_site_graph()
    builder.load_faculty_data()
    builder.merge_research_cards()
    builder.export()
