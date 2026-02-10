import networkx as nx
from typing import List, Dict, Any, Tuple
from enum import Enum
import hashlib
from rich.console import Console
from .entity_extraction import EntityExtractor  # We'll create this helper

console = Console()

class QueryType(Enum):
    FACTOID = "factoid"      # "What is Zero-Shot Learning?"
    ENTITY = "entity"        # "Who works on X?"
    RELATIONAL = "relational"# "Compare A and B"
    EXPLORATORY = "exploratory" # "What's new in Y?"

class HybridRetriever:
    """
    Adaptive retrieval engine that routes queries to the optimal strategy
    based on intent (Sequential vs Parallel).
    """
    
    # Keywords for heuristic classification (Fast, no LLM)
    ENTITY_KEYWORDS = [
        "who", "which faculty", "researcher", "author", "professor", 
        "expert", "lab", "team", "person", "faculty"
    ]
    FACTOID_KEYWORDS = [
        "what is", "define", "explain", "how does", "describe", 
        "concept", "meaning", "definition"
    ]
    COMPARE_KEYWORDS = ["compare", "difference", "versus", "vs", "similarities"]
    
    def __init__(self, vector_db, graph_path: str):
        self.vector_db = vector_db
        console.print(f"[cyan]Loading Knowledge Graph for Retrieval...[/]")
        
        # Load JSON graph instead of GML
        import json
        from networkx.readwrite import node_link_graph
        from pathlib import Path
        
        json_path = Path(graph_path).with_suffix('.json')
        with open(json_path, 'r') as f:
            data = json.load(f)
        self.graph = node_link_graph(data)
        
        console.print(f"[green]Graph Loaded: {self.graph.number_of_nodes()} nodes[/]")
        
        # Initialize fast entity extractor (Graph Index)
        self.entity_extractor = EntityExtractor(self.graph)

    def classify_query(self, query: str) -> QueryType:
        """
        Classifies query intent using keyword heuristics.
        Returns: QueryType
        """
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in self.FACTOID_KEYWORDS):
            return QueryType.FACTOID
        elif any(kw in query_lower for kw in self.ENTITY_KEYWORDS):
            return QueryType.ENTITY
        elif any(kw in query_lower for kw in self.COMPARE_KEYWORDS):
            return QueryType.RELATIONAL
        else:
            return QueryType.EXPLORATORY

    def retrieve(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Main entry point. Routes to specific retrieval strategy.
        """
        query_type = self.classify_query(query)
        console.print(f"[bold blue]Query Type Classified: {query_type.value}[/]")
        
        if query_type == QueryType.FACTOID:
            # Parallel: Speed matters for definitions
            return self._parallel_retrieve(query, limit)
        else:
            # Sequential: Precision matters for research/entity queries
            return self._sequential_retrieve(query, limit)

    def _sequential_retrieve(self, query: str, limit: int) -> Dict[str, Any]:
        """
        Graph-First Strategy:
        1. Extract entities from query (using Graph Index)
        2. Traverse graph specific hops (Paper -> Concept -> Paper)
        3. Vector search (filtered/boosted by graph context)
        """
        # Step 1: Fast Entity Extraction
        entities = self.entity_extractor.extract(query)
        console.print(f"[dim]Extracted Entities: {[e['label'] for e in entities]}[/]")
        
        graph_docs = []
        exclude_ids = set()

        # Step 2: Graph Traversal (Targeting Faculty & Papers)
        if entities:
            # If we found concepts/faculty in query, get their neighborhood
            # for 1-2 hops.
            for entity in entities:
                node_id = entity['id']
                # Get neighbors (Papers written by Faculty, or Papers mentoring Concept)
                # Handle directed graph: we want both precursors (Papers -> Concept) and successors
                if self.graph.is_directed():
                    neighbors = list(self.graph.predecessors(node_id)) + list(self.graph.successors(node_id))
                else:
                    neighbors = list(self.graph.neighbors(node_id))
                
                for n in neighbors:
                    node_data = self.graph.nodes[n]
                    if node_data.get('type') == 'paper':
                        # 2-hop retrieval: Find authors of this paper
                        authors = []
                        # Check neighbors of the paper for faculty
                        if self.graph.is_directed():
                            paper_neighbors = list(self.graph.predecessors(n)) + list(self.graph.successors(n))
                        else:
                            paper_neighbors = self.graph.neighbors(n)
                            
                        for pn in paper_neighbors:
                            p_data = self.graph.nodes[pn]
                            if p_data.get('type') == 'faculty':
                                author_name = p_data.get('name', p_data.get('label', 'Unknown'))
                                authors.append(author_name)
                                
                                # Add Faculty node explicitly to results if not already present
                                if pn not in exclude_ids:
                                    # Create a rich text representation for the LLM
                                    bio = p_data.get('bio', '') or "No bio available."
                                    dept = p_data.get('department', '') or "Unknown Dept"
                                    interests = p_data.get('research_interests', [])
                                    if isinstance(interests, list):
                                        interests = ", ".join(interests)
                                    
                                    faculty_doc = {
                                        "id": pn,
                                        "text": f"Professor: {author_name}\nDepartment: {dept}\nBio: {bio}\nInterests: {interests}",
                                        "metadata": {
                                            "type": "faculty_profile",
                                            "source_node": entity['label'],
                                            "title": author_name
                                        },
                                        "score": 1.2 # Boost faculty score
                                    }
                                    graph_docs.append(faculty_doc)
                                    exclude_ids.add(pn)
                        
                        author_str = f" (Authored by: {', '.join(authors)})" if authors else ""
                        
                        doc = {
                            "id": n,
                            "text": f"Paper: {node_data.get('label', '')}{author_str}",
                            "metadata": {
                                "type": "research_paper", 
                                "source_node": entity['label'],
                                "authors": authors,
                                "title": node_data.get('label', '')
                            },
                            "score": 1.0
                        }
                        graph_docs.append(doc)
                        exclude_ids.add(n)

        # Step 3: Vector Search (Supplement)
        # We query vector DB but exclude what we already found in graph?
        # Or better: Get vector results and merge strategies later (Fusion phase).
        # For now, let's get raw vector results.
        vector_docs = self.vector_db.search(query, limit=limit)
        
        return {
            "strategy": "sequential",
            "graph_results": graph_docs[:limit],
            "vector_results": vector_docs,
            "entities": entities
        }

    def _parallel_retrieve(self, query: str, limit: int) -> Dict[str, Any]:
        """
        Parallel Strategy:
        Run Vector Search and simple Graph Concept lookup in parallel.
        """
        # Simple graph lookup (just matches)
        entities = self.entity_extractor.extract(query)
        graph_docs = []
        for entity in entities:
             # Just add the entity node itself as a result
             graph_docs.append({
                 "id": entity['id'],
                 "text": entity['label'], 
                 "metadata": self.graph.nodes[entity['id']],
                 "score": 1.0
             })

        vector_docs = self.vector_db.search(query, limit=limit)
        
        return {
            "strategy": "parallel",
            "graph_results": graph_docs,
            "vector_results": vector_docs,
            "entities": entities
        }
