"""Knowledge Graph Builder for TigerResearchBuddy.

Constructs a NetworkX graph from faculty, papers, and research data.
"""

import json
import hashlib
import pickle
from pathlib import Path
from typing import Optional
import networkx as nx
from rich.console import Console

console = Console()

# Data directories
DATA_DIR = Path("data")
PAPERS_DIR = DATA_DIR / "papers"
GRAPH_PATH = DATA_DIR / "knowledge_graph.pkl"


class KnowledgeGraphBuilder:
    """Build and manage the knowledge graph."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def build_from_data(self):
        """Build graph from all available data sources."""
        console.print("[bold blue]🔨 Building Knowledge Graph...[/]")
        
        # Load RIT data
        rit_data_path = DATA_DIR / "comprehensive_data.json"
        if rit_data_path.exists():
            with open(rit_data_path) as f:
                rit_data = json.load(f)
            self._add_rit_data(rit_data)
        
        # Load papers
        self._add_papers()
        
        #compute relationships
        self._compute_relationships()
        
        stats = self.get_stats()
        console.print(f"[green]✓ Graph built: {stats['nodes']} nodes, {stats['edges']} edges[/]")
        
        return self.graph
    
    def _add_rit_data(self, rit_data: dict):
        """Add faculty and research areas from RIT data."""
        console.print("[dim]Adding faculty and topics...[/]")
        
        # Add faculty
        for faculty in rit_data.get("faculty", []):
            faculty_id = f"faculty_{self._hash_id(faculty['name'])}"
            
            self.graph.add_node(
                faculty_id,
                type="faculty",
                name=faculty["name"],
                title=faculty.get("title", ""),
                email=faculty.get("email", ""),
                department=faculty.get("department", ""),
                research_interests=faculty.get("research_interests", ""),
            )
            
            # Link faculty to their auto_tags as topics
            for tag in faculty.get("auto_tags", [])[:10]:  # Top 10 tags
                topic_id = f"topic_{tag}"
                
                # Add topic node if not exists
                if not self.graph.has_node(topic_id):
                    self.graph.add_node(
                        topic_id,
                        type="topic",
                        name=tag,
                        category="research",
                    )
                
                # Link faculty to topic
                self.graph.add_edge(
                    faculty_id,
                    topic_id,
                    type="works_on",
                    weight=1.0,
                )
    
    def _add_papers(self):
        """Add papers from the papers directory."""
        console.print("[dim]Adding research papers...[/]")
        
        if not PAPERS_DIR.exists():
            return
        
        for paper_file in PAPERS_DIR.glob("*.json"):
            try:
                with open(paper_file) as f:
                    paper = json.load(f)
                
                title = paper.get("title", "")
                if not title:
                    continue
                
                paper_id = f"paper_{self._hash_id(title)}"
                
                # Add paper node
                self.graph.add_node(
                    paper_id,
                    type="paper",
                    title=title[:200],
                    authors=paper.get("authors", []),
                    year=paper.get("year", ""),
                    abstract=paper.get("abstract", "")[:500],
                    source=paper.get("source", ""),
                )
                
                # Link paper to faculty (authors)
                faculty_name = paper.get("faculty", "")
                if faculty_name:
                    faculty_id = f"faculty_{self._hash_id(faculty_name)}"
                    if self.graph.has_node(faculty_id):
                        self.graph.add_edge(
                            faculty_id,
                            paper_id,
                            type="authored",
                            weight=1.0,
                        )
                
                # Extract tags from metadata
                tags_data = []
                tags_str = paper.get("tags", "")
                if isinstance(tags_str, str) and tags_str:
                    try:
                        tags_data = json.loads(tags_str)
                    except:
                        pass
                
                # Add topics from tags
                for tag_name in tags_data[:15]:  # Top 15 tags
                    if isinstance(tag_name, str) and tag_name:
                        topic_id = f"topic_{tag_name}"
                        
                        # Add topic node if not exists
                        if not self.graph.has_node(topic_id):
                            self.graph.add_node(
                                topic_id,
                                type="topic",
                                name=tag_name,
                                category="research",
                            )
                        
                        # Link paper to topic
                        self.graph.add_edge(
                            paper_id,
                            topic_id,
                            type="about",
                            weight=0.7,  # Default confidence
                        )
                        
                        # Link faculty to topic (strengthen connection)
                        if faculty_name:
                            faculty_id = f"faculty_{self._hash_id(faculty_name)}"
                            if self.graph.has_node(faculty_id):
                                # Aggregate weight if edge exists
                                if self.graph.has_edge(faculty_id, topic_id):
                                    current_weight = self.graph[faculty_id][topic_id]["weight"]
                                    self.graph[faculty_id][topic_id]["weight"] = current_weight + 0.3
                                else:
                                    self.graph.add_edge(
                                        faculty_id,
                                        topic_id,
                                        type="works_on",
                                        weight=0.3,
                                    )
            
            except Exception as e:
                console.print(f"[yellow]Error adding paper {paper_file.name}: {e}[/]")
    
    def _compute_relationships(self):
        """Compute derived relationships like collaborations."""
        console.print("[dim]Computing collaborations...[/]")
        
        # Find collaborations (shared papers)
        faculty_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "faculty"]
        
        for i, faculty1 in enumerate(faculty_nodes):
            # Get papers authored by faculty1
            papers1 = set(successor for successor in self.graph.successors(faculty1)
                         if self.graph.nodes[successor].get("type") == "paper")
            
            for faculty2 in faculty_nodes[i+1:]:
                # Get papers authored by faculty2
                papers2 = set(successor for successor in self.graph.successors(faculty2)
                             if self.graph.nodes[successor].get("type") == "paper")
                
                # Check for shared papers
                shared_papers = papers1 & papers2
                
                if shared_papers:
                    # Add collaboration edge
                    weight = len(shared_papers)
                    self.graph.add_edge(
                        faculty1,
                        faculty2,
                        type="collaborates_with",
                        weight=weight,
                        shared_papers=list(shared_papers),
                    )
                    # Add reverse edge
                    self.graph.add_edge(
                        faculty2,
                        faculty1,
                        type="collaborates_with",
                        weight=weight,
                        shared_papers=list(shared_papers),
                    )
    
    def _hash_id(self, text: str) -> str:
        """Create a short hash ID from text."""
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    def save(self, path: Optional[Path] = None):
        """Save graph to disk."""
        path = path or GRAPH_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump(self.graph, f)
        
        console.print(f"[green]✓ Graph saved to {path}[/]")
    
    def load(self, path: Optional[Path] = None) -> Optional[nx.DiGraph]:
        """Load graph from disk."""
        path = path or GRAPH_PATH
        
        if not path.exists():
            return None
        
        with open(path, "rb") as f:
            self.graph = pickle.load(f)
        
        console.print(f"[green]✓ Graph loaded from {path}[/]")
        return self.graph
    
    def get_stats(self) -> dict:
        """Get graph statistics."""
        node_types = {}
        for node, data in self.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        edge_types = {}
        for u, v, data in self.graph.edges(data=True):
            edge_type = data.get("type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types,
        }


def build_knowledge_graph(force_rebuild: bool = False) -> nx.DiGraph:
    """Build or load the knowledge graph."""
    builder = KnowledgeGraphBuilder()
    
    if not force_rebuild and GRAPH_PATH.exists():
        graph = builder.load()
        if graph is not None:
            return graph
    
    # Build from scratch
    graph = builder.build_from_data()
    builder.save()
    
    return graph


if __name__ == "__main__":
    # Build and save the graph
    graph = build_knowledge_graph(force_rebuild=True)
    
    builder = KnowledgeGraphBuilder()
    builder.graph = graph
    stats = builder.get_stats()
    
    console.print("\n[bold]Knowledge Graph Statistics:[/]")
    console.print(f"Total Nodes: {stats['nodes']}")
    console.print(f"Total Edges: {stats['edges']}")
    console.print("\n[bold]Node Types:[/]")
    for node_type, count in stats['node_types'].items():
        console.print(f"  {node_type}: {count}")
    console.print("\n[bold]Edge Types:[/]")
    for edge_type, count in stats['edge_types'].items():
        console.print(f"  {edge_type}: {count}")
