"""Graph query interface for KuzuDB knowledge graph."""

from typing import List, Dict, Optional
from .graph_store import GraphStore

class GraphQueries:
    """Query interface for the knowledge graph."""
    
    def __init__(self, store: GraphStore):
        self.store = store
    
    def find_faculty_by_name(self, name: str) -> Optional[str]:
        """Find faculty node ID (name) by name (fuzzy match)."""
        # Kuzu doesn't have native fuzzy match effectively in Cypher yet for this version,
        # but we can do a CONTAINS search or just exact match for now.
        # We will retrieve all faculty and fuzzy match in Python if needed, 
        # or just use simple string matching in Cypher.
        
        # Simple case-insensitive containment
        query = f"""
        MATCH (f:Faculty)
        WHERE lower(f.name) CONTAINS lower($name)
        RETURN f.name
        LIMIT 1
        """
        result = self.store.execute(query, {"name": name})
        if result.has_next():
            return result.get_next()[0]
        return None
    
    def get_collaborators(self, faculty_name: str) -> List[Dict]:
        """Find all collaborators of a faculty member."""
        query = """
        MATCH (a:Faculty)-[r:CollaboratesWith]->(b:Faculty)
        WHERE a.name = $name
        RETURN b.name, r.weight
        ORDER BY r.weight DESC
        """
        results = self.store.execute(query, {"name": faculty_name})
        
        collaborators = []
        while results.has_next():
            row = results.get_next()
            collaborators.append({
                "id": row[0],
                "name": row[0],
                "shared_papers": row[1]
            })
        return collaborators
    
    def get_faculty_expertise(self, faculty_name: str) -> List[Dict]:
        """Get research topics/areas for a faculty member."""
        # Mentions Topic
        query_topics = """
        MATCH (f:Faculty)-[r:Mentions]->(t:Topic)
        WHERE f.name = $name
        RETURN t.name, 'topic', r.weight
        ORDER BY r.weight DESC
        LIMIT 10
        """
        # WorksOn Concept
        query_concepts = """
        MATCH (f:Faculty)-[r:WorksOn]->(c:Concept)
        WHERE f.name = $name
        RETURN c.name, 'concept', r.weight
        ORDER BY r.weight DESC
        LIMIT 10
        """
        
        topics = []
        
        # Topics
        res_t = self.store.execute(query_topics, {"name": faculty_name})
        while res_t.has_next():
            row = res_t.get_next()
            topics.append({"topic": row[0], "category": row[1], "weight": row[2]})
            
        # Concepts
        res_c = self.store.execute(query_concepts, {"name": faculty_name})
        while res_c.has_next():
            row = res_c.get_next()
            topics.append({"topic": row[0], "category": row[1], "weight": row[2]})
            
        return sorted(topics, key=lambda x: x["weight"], reverse=True)
    
    def find_experts_in_topic(self, topic: str, top_k: int = 10) -> List[Dict]:
        """Find faculty who work on a specific topic or concept."""
        # KuzuDB doesn't fully support OR in label filtering in WHERE clause easily in all versions.
        # Using UNION is safer.
        
        query = """
        MATCH (f:Faculty)-[r]->(n:Topic)
        WHERE lower(n.name) CONTAINS lower($topic)
        RETURN f.name, f.department, r.weight as w
        UNION ALL
        MATCH (f:Faculty)-[r]->(n:Concept)
        WHERE lower(n.name) CONTAINS lower($topic)
        RETURN f.name, f.department, r.weight as w
        """
        
        # We need to aggregate manually since UNION ALL returns rows
        # Actually Kuzu might not support aggregation over UNION directly in subquery easily.
        # Let's just fetch and aggregate in Python for simplicity and robustness.
        
        results = self.store.execute(query, {"topic": topic})
        
        faculty_weights = {}
        faculty_depts = {}
        
        while results.has_next():
            row = results.get_next()
            name = row[0]
            dept = row[1]
            weight = row[2]
            
            faculty_weights[name] = faculty_weights.get(name, 0) + weight
            faculty_depts[name] = dept
            
        experts = []
        for name, weight in faculty_weights.items():
            experts.append({
                "id": name,
                "name": name,
                "department": faculty_depts.get(name, ""),
                "expertise_weight": weight
            })
            
        return sorted(experts, key=lambda x: x["expertise_weight"], reverse=True)[:top_k]
    
    def get_faculty_papers(self, faculty_name: str) -> List[Dict]:
        """Get all papers authored by a faculty member."""
        query = """
        MATCH (f:Faculty)-[:Authored]->(p:Paper)
        WHERE f.name = $name
        RETURN p.paper_id, p.title, p.year
        ORDER BY p.year DESC
        """
        results = self.store.execute(query, {"name": faculty_name})
        
        papers = []
        while results.has_next():
            row = results.get_next()
            papers.append({
                "id": row[0],
                "title": row[1],
                "year": row[2],
                # Authors list is hard to reconstruct efficiently in one query without collect() 
                # grouping which might be slow. Omitted for preview.
                "authors": [] 
            })
        return papers
    
    def find_research_clusters(self, min_size: int = 3) -> List[Dict]:
        """
        Find research clusters using Weakly Connected Components or similar.
        KuzuDB has some graph algos, but simplified approach here:
        Find cliques or dense subgraphs via Python networkx on subgraph?
        
        For now, let's just find "Frequent Collaborations" triples as a proxy for clusters.
        A-B, B-C, A-C
        """
        query = """
        MATCH (a:Faculty)-[:CollaboratesWith]->(b:Faculty)-[:CollaboratesWith]->(c:Faculty)
        MATCH (a:Faculty)-[:CollaboratesWith]->(c:Faculty)
        WHERE a.name < b.name AND b.name < c.name
        RETURN a.name, b.name, c.name
        LIMIT 5
        """
        results = self.store.execute(query)
        
        clusters = []
        idx = 0
        while results.has_next():
            row = results.get_next()
            clusters.append({
                "cluster_id": idx,
                "size": 3,
                "members": [{"name": row[0]}, {"name": row[1]}, {"name": row[2]}]
            })
            idx += 1
            
        return clusters
