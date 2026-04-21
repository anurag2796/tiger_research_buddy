"""Knowledge Graph Builder for TigerResearchBuddy.

Constructs a NetworkX graph from faculty, papers, and research data.
"""

import json
import hashlib
import pickle
from pathlib import Path
from typing import Optional
# import networkx as nx # Deprecated
from rich.console import Console

from ..utils.config import DATA_DIR
from ..utils.timer import Timer
from .graph_store import GraphStore

console = Console()

# Data directories
# DATA_DIR is imported from config now
PAPERS_DIR = DATA_DIR / "papers"
GRAPH_DB_PATH = DATA_DIR / "kuzu_db"


class KnowledgeGraphBuilder:
    """Build and manage the knowledge graph using KuzuDB."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        # Initialize GraphStore
        self.store = GraphStore(GRAPH_DB_PATH)
        
    def build_from_data(self, rit_data_file: Optional[Path] = None):
        """Build graph from all available data sources."""
        with Timer("Building Knowledge Graph (KuzuDB)", use_rich=True):
            # Load RIT data
            rit_data_path = rit_data_file or (self.data_dir / "comprehensive_data.json")
            if rit_data_path.exists():
                with open(rit_data_path) as f:
                    rit_data = json.load(f)
                with Timer("Adding RIT Data", use_rich=False):
                    self._add_rit_data(rit_data)
            
            
            # Load papers (legacy)
            with Timer("Adding Papers (Legacy)", use_rich=False):
                self._add_papers()
            
            # Load Research Cards (TigerCard 2.0)
            with Timer("Adding Research Cards", use_rich=False):
                self._add_research_cards()
            
            #compute relationships
            with Timer("Computing Relationships (Cypher)", use_rich=False):
                self._compute_relationships()
        
        console.print(f"[green]✓ Graph built in {GRAPH_DB_PATH}[/]")
        # return self.graph # No longer returning NX graph
    
    def _add_rit_data(self, rit_data: dict):
        """Add faculty and research areas from RIT data."""
        console.print("[dim]Adding faculty and topics...[/]")
        
        # Add faculty
        for faculty in rit_data.get("faculty", []):
            # Kuzu uses 'name' as PK for Faculty
            self.store.add_faculty(faculty)
            
            # Link faculty to their auto_tags as topics
            for tag in faculty.get("auto_tags", [])[:10]:  # Top 10 tags
                topic_id = f"topic_{self._hash_id(tag)}"
                
                # Add topic
                self.store.add_topic(topic_id, tag, "research")
                
                # Link
                self.store.add_works_on(faculty["name"], topic_id, weight=1.0)
    
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
                
                # Add paper node
                paper_id = f"paper_{self._hash_id(title)}"
                paper_data = {
                    "paper_id": paper_id,
                    "title": title[:200],
                    "year": paper.get("year", 0),
                    "venue": paper.get("source", ""),
                    "abstract": paper.get("abstract", "")[:500]
                }
                self.store.add_paper(paper_data)
                
                # Link paper to faculty (authors)
                faculty_name = paper.get("faculty", "")
                if faculty_name:
                    self.store.add_author_rel(faculty_name, paper_id)
                
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
                        topic_id = f"topic_{self._hash_id(tag_name)}"
                        self.store.add_topic(topic_id, tag_name, "research")
                        
                        # Link paper to topic
                        # self.store.add_about(paper_id, topic_id, weight=0.7) # Need to impl this in Store if needed
                        
                        # Link faculty to topic (strengthen connection)
                        if faculty_name:
                            self.store.add_works_on(faculty_name, topic_id, weight=0.3)
            
            except Exception as e:
                console.print(f"[yellow]Error adding paper {paper_file.name}: {e}[/]")

    def _add_research_cards(self):
        """Add nodes from distilled Research Cards."""
        cards_dir = DATA_DIR / "research_cards"
        if not cards_dir.exists():
            return

        console.print("[dim]Ingesting Research Cards (TigerCard 2.0)...[/]")
        
        for card_file in cards_dir.glob("*.json"):
            try:
                with open(card_file) as f:
                    card = json.load(f)
                
                # Check for valid schema
                if "card_id" not in card:
                    continue
                    
                bib = card.get("bibliographic_data", {})
                core = card.get("core_content", {})
                kg = card.get("knowledge_graph", {})
                
                title = bib.get("title", "Untitled Paper")
                paper_id = f"paper_{self._hash_id(title)}"
                
                # 1. Create Paper Node
                paper_id = f"paper_{self._hash_id(title)}"
                
                paper_data = {
                    "paper_id": paper_id,
                    "title": title,
                    "year": bib.get("year", 0),
                    "venue": bib.get("venue", ""),
                    "domain": bib.get("primary_domain", ""),
                    "novelty": core.get("novelty_claim", ""),
                    "outcomes": json.dumps(core.get("outcomes", [])),
                    "source_file": card.get("source_file", "")
                }
                self.store.add_paper(paper_data)
                
                # 2. Link Authors (Faculty)
                authors = bib.get("authors", [])
                for author in authors:
                    author_name = author if isinstance(author, str) else author.get("name")
                    if not author_name: continue
                    
                    self.store.add_author_rel(author_name, paper_id)

                # 3. Ingest Concepts from KG section
                for node in kg.get("nodes", []):
                    concept_id = f"concept_{node.get('id', self._hash_id(node.get('label')))}"
                    label = node.get("label", "Unknown")
                    cnt_type = node.get("type", "Concept")
                    
                    self.store.add_concept(concept_id, label, cnt_type)
                    
                    # Link Paper -> Concept
                    self.store.add_mentions(paper_id, concept_id)

                # 4. Ingest Edges from KG section (Concept -> Concept)
                for edge in kg.get("edges", []):
                    src_id = f"concept_{edge.get('source')}"
                    tgt_id = f"concept_{edge.get('target')}"
                    relation = edge.get("relation", "RELATED_TO")
                    
                    # Note: We can't easily check 'if node exists' without query, 
                    # but create_rel_table IF NOT EXISTS or triggers handle safety usually.
                    # Kuzu will error if nodes don't exist.
                    # For now, trust the KG extractor logic or ignore errors
                    try:
                        self.store.add_related(src_id, tgt_id, relation, 0.5)
                    except Exception:
                        pass

            except Exception as e:
                console.print(f"[red]Error ingesting card {card_file.name}: {e}[/]")
    
    def _compute_relationships(self):
        """Compute derived relationships using Cypher queries."""
        console.print("[dim]Computing collaborations via Cypher...[/]")
        
        # Collaborative query:
        # Match two faculty who authored the SAME paper
        # Count the number of shared papers
        query = """
        MATCH (a:Faculty)-[:Authored]->(p:Paper)<-[:Authored]-(b:Faculty)
        WHERE a.name < b.name
        RETURN a.name, b.name, count(p) as shared_count
        """
        
        results = self.store.execute(query)
        
        count = 0
        while results.has_next():
            row = results.get_next()
            fac_a, fac_b, weight = row[0], row[1], row[2]
            self.store.add_collaboration(fac_a, fac_b, weight)
            count += 1
            
        console.print(f"[dim]Computed {count} collaboration pairs[/]")
    
    def _hash_id(self, text: str) -> str:
        """Create a short hash ID from text."""
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    # Save/Load are handled by KuzuDB implicitly    
    def get_stats(self) -> dict:
        """Get graph statistics via Queries."""
        # Simple counts
        nodes = 0
        node_types = {}
        edge_types = {}

        # Create list as local var to avoid SyntaxError in f-string
        tables = ["Faculty", "Paper", "Concept", "Topic"]

        # Optimization: Use UNION ALL to combine multiple count queries into one
        # This avoids N+1 query pattern for node counts
        query = " UNION ALL ".join(
            [f"MATCH (n:{table}) RETURN '{table}' as label, count(n) as count" for table in tables]
        )
        results = self.store.execute(query)

        while results.has_next():
            row = results.get_next()
            label, count = row[0], row[1]
            node_types[label] = count
            nodes += count

        return {
            "nodes": nodes,
            "edges": "Approximated (Unknown)",  # Kuzu doesn't give global edge count easily without iterating all tables
            "node_types": node_types,
            "edge_types": edge_types,
        }


def build_knowledge_graph(force_rebuild: bool = False) -> None:
    """Build or load the knowledge graph."""
    # Kuzu is persistent, so 'rebuild' might mean dropping the DB.
    # For now, we always init the builder, which connects to existing DB.
    # explicit rebuild logic would go here.
    
    builder = KnowledgeGraphBuilder()
    
    # If force_rebuild, we might ideally drop tables, but here we just run build_from_data
    # which performs MERGE operations (upsert).
    builder.build_from_data()
    return None



if __name__ == "__main__":
    # Build the graph
    build_knowledge_graph(force_rebuild=True)
    
    builder = KnowledgeGraphBuilder()
    stats = builder.get_stats()
    
    console.print("\n[bold]Knowledge Graph Statistics (Node Counts):[/]")
    console.print(f"Total Nodes: {stats['nodes']}")
    console.print("\n[bold]Node Types:[/]")
    for node_type, count in stats['node_types'].items():
        console.print(f"  {node_type}: {count}")
