import json
import re
import networkx as nx
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import track
from src.knowledge_graph.entity_resolver import EntityResolver
from src.utils.config import CrawlConfig, DATA_DIR

console = Console()

class GraphBuilder:
    def __init__(self, data_dir: str = "data", config: Optional[CrawlConfig] = None):
        self.data_dir = Path(data_dir)
        self.config = config
        # Use config-aware paths if available, else fall back to data_dir defaults
        if config:
            self.site_graph_path = config.BASE_DIR / "site_graph.gml"
            self.cards_dir = config.BASE_DIR / "research_cards"
            self.faculty_json_path = config.OUTPUT_FILE
        else:
            self.site_graph_path = self.data_dir / "site_graph.gml"
            self.cards_dir = self.data_dir / "research_cards"
            self.faculty_json_path = self.data_dir / "rit_data_v2.json"
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
        json_path = self.faculty_json_path
        
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

        # Cache faculty node names (lowercase → canonical) for fast lookup
        faculty_name_index: dict[str, str] = {}
        for n, d in self.graph.nodes(data=True):
            if d.get("type") == "faculty" and n:
                faculty_name_index[str(n).lower()] = str(n)

        console.print(f"[cyan]Integrating {len(json_files)} Research Cards with {len(faculty_name_index)} Faculty nodes...[/]")

        authored_edges = 0

        for json_file in track(json_files, description="Merging Knowledge..."):
            try:
                with open(json_file, "r") as f:
                    card = json.load(f)

                bib = card.get("bibliographic_data") or {}
                core = card.get("core_content") or {}

                paper_title = bib.get("title") or card.get("title") or "Unknown Paper"
                paper_year = bib.get("year") or card.get("year", "")
                raw_authors = bib.get("authors") or card.get("authors", [])

                paper_id = f"paper_{paper_title.lower().replace(' ', '_')}"[:50]

                # 1. Add Paper Node
                self.graph.add_node(paper_id, type="paper", label=paper_title, year=str(paper_year))

                # 2. Link RIT Faculty Authors
                # Priority: use faculty_id field if present (authoritative); fall back to
                # entity resolver for names that were extracted without explicit faculty_id.
                rit_authors_on_paper: list[str] = []

                for a in raw_authors:
                    if not isinstance(a, dict) or "name" not in a:
                        continue

                    author_name: str = a["name"]
                    affiliation: str = a.get("affiliation", "")
                    faculty_id_hint: str = a.get("faculty_id", "")

                    canonical_name: Optional[str] = None

                    # Fast path: faculty_id is the canonical graph node name
                    if faculty_id_hint and faculty_id_hint.lower() in faculty_name_index:
                        canonical_name = faculty_name_index[faculty_id_hint.lower()]
                    elif faculty_id_hint and self.graph.has_node(faculty_id_hint):
                        canonical_name = faculty_id_hint
                    elif affiliation.upper() == "RIT" or affiliation == "":
                        # Slow path: use entity resolver for fuzzy name matching
                        cid = self.entity_resolver.resolve_faculty(author_name, department=affiliation)
                        cname = (
                            self.entity_resolver.canonical_entities
                            .get(cid, {})
                            .get("canonical_name", author_name)
                        )
                        if self.graph.has_node(cname):
                            canonical_name = cname
                        else:
                            # Last resort: case-insensitive direct lookup
                            canonical_name = faculty_name_index.get(author_name.lower())

                    if canonical_name and self.graph.has_node(canonical_name):
                        self.graph.add_edge(canonical_name, paper_id, type="AUTHORED", weight=1.0)
                        rit_authors_on_paper.append(canonical_name)
                        authored_edges += 1

                # 3. Connect RIT co-authors to each other through shared papers
                for i, fa in enumerate(rit_authors_on_paper):
                    for fb in rit_authors_on_paper[i + 1:]:
                        if self.graph.has_edge(fa, fb):
                            self.graph.edges[fa, fb]["weight"] = (
                                self.graph.edges[fa, fb].get("weight", 1.0) + 1.0
                            )
                        else:
                            self.graph.add_edge(fa, fb, type="COAUTHORED_WITH", weight=1.0)

                # 4. Add Concepts & Relations
                kg = card.get("knowledge_graph") or {}
                nodes = kg.get("nodes", kg.get("entities", []))
                edges = kg.get("edges", kg.get("relations", []))

                local_id_map = {}

                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    local_id = node.get("id")
                    concept_label = node.get("label", node.get("name", ""))
                    concept_type = node.get("type", "concept")

                    if not local_id or not concept_label:
                        continue

                    normalized = re.sub(r"[^a-z0-9\s]", "", concept_label.lower())
                    normalized = re.sub(r"\s+", "_", normalized.strip())
                    global_id = f"concept__{normalized.rstrip('s') if len(normalized) > 4 else normalized}"
                    local_id_map[local_id] = global_id

                    if not self.graph.has_node(global_id):
                        self.graph.add_node(global_id, type="concept", label=concept_label, concept_type=concept_type)

                    self.graph.add_edge(paper_id, global_id, type="MENTIONS", weight=1.0)

                for edge in edges:
                    if not isinstance(edge, dict):
                        continue
                    src = local_id_map.get(edge.get("source"))
                    tgt = local_id_map.get(edge.get("target"))
                    rel_type = edge.get("relation", edge.get("type", "RELATED_TO"))

                    if src and tgt and self.graph.has_node(src) and self.graph.has_node(tgt):
                        self.graph.add_edge(src, tgt, type=rel_type, weight=0.5)

                # 5. Fallback keywords as concepts
                keywords = card.get("keywords", [])
                if not keywords and core:
                    keywords = core.get("keywords", [])

                for keyword in keywords:
                    if not keyword or len(keyword) < 3:
                        continue
                    concept_id = f"kw_{keyword.lower().replace(' ', '_')}"
                    if not self.graph.has_node(concept_id):
                        self.graph.add_node(concept_id, type="concept", name=keyword, concept_type="keyword")
                    self.graph.add_edge(paper_id, concept_id, type="HAS_TOPIC", weight=0.8)

            except Exception as e:
                console.print(f"[yellow]Skipping {json_file.name}: {e}[/]")

        console.print(f"[green]Created {authored_edges} faculty→paper AUTHORED edges.[/]")

    def prune_sparse_concepts(self, min_papers: int = 2):
        """Remove concept nodes connected to fewer than min_papers papers.

        Singleton concepts are per-paper noise that balloon node count and
        fragment the layout without adding cross-faculty connectivity.
        """
        to_remove = []
        for n, d in self.graph.nodes(data=True):
            if d.get("type") != "concept":
                continue
            # In a DiGraph, neighbors() only returns successors. 
            # We must check predecessors (incoming edges) as papers point to concepts.
            paper_neighbors = sum(
                1 for nb in (list(self.graph.predecessors(n)) + list(self.graph.successors(n)))
                if self.graph.nodes[nb].get("type") == "paper"
            )
            if paper_neighbors < min_papers:
                to_remove.append(n)
        self.graph.remove_nodes_from(to_remove)
        console.print(f"[cyan]Pruned {len(to_remove)} singleton concept nodes (kept concepts appearing in {min_papers}+ papers).[/]")

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
        """Save the fused graph (Fix 6: atomic write with file lock)."""
        self.sanitize_graph()
        try:
            # Use JSON format instead of GML to preserve all node attributes
            import json
            import filelock
            from networkx.readwrite import node_link_data
            
            # Change output path from .gml to .json
            json_path = self.output_path.with_suffix('.json')
            lock_path = json_path.parent / ".graph.lock"
            
            data = node_link_data(self.graph)
            with filelock.FileLock(lock_path):
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
    builder.prune_sparse_concepts(min_papers=2)
    builder.export()
