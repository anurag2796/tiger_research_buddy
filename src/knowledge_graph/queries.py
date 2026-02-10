"""Graph query interface for knowledge graph."""

import networkx as nx
from typing import List, Dict, Optional, Tuple


class GraphQueries:
    """Query interface for the knowledge graph."""
    
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
    
    def find_faculty_by_name(self, name: str) -> Optional[str]:
        """Find faculty node ID by name (fuzzy match)."""
        name_lower = name.lower()
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "faculty":
                faculty_name = data.get("name", "").lower()
                if name_lower in faculty_name or faculty_name in name_lower:
                    return node
        return None
    
    def get_collaborators(self, faculty_id: str) -> List[Dict]:
        """Find all collaborators of a faculty member."""
        collaborators = []
        
        for successor in self.graph.successors(faculty_id):
            edge_data = self.graph[faculty_id][successor]
            if edge_data.get("type") == "collaborates_with":
                collab_data = self.graph.nodes[successor]
                collaborators.append({
                    "id": successor,
                    "name": collab_data.get("name", ""),
                    "shared_papers": edge_data.get("weight", 0),
                })
        
        return sorted(collaborators, key=lambda x: x["shared_papers"], reverse=True)
    
    def get_faculty_expertise(self, faculty_id: str) -> List[Dict]:
        """Get research topics/areas for a faculty member."""
        topics = []
        
        for successor in self.graph.successors(faculty_id):
            edge_data = self.graph[faculty_id][successor]
            node_data = self.graph.nodes[successor]
            node_type = node_data.get("type")
            
            if node_type == "topic":
                topics.append({
                    "topic": node_data.get("name", ""),
                    "category": node_data.get("category", ""),
                    "weight": edge_data.get("weight", 0),
                })
            elif node_type == "research_area":
                topics.append({
                    "topic": node_data.get("name", ""),
                    "category": "research_area",
                    "weight": edge_data.get("weight", 0),
                })
        
        return sorted(topics, key=lambda x: x["weight"], reverse=True)
    
    def find_experts_in_topic(self, topic: str, top_k: int = 10) -> List[Dict]:
        """Find faculty who work on a specific topic."""
        topic_lower = topic.lower()
        experts = []
        
        # Find matching topic nodes
        topic_nodes = []
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "topic":
                if topic_lower in data.get("name", "").lower():
                    topic_nodes.append(node)
        
        # Find faculty connected to these topics
        faculty_weights = {}
        for topic_node in topic_nodes:
            for predecessor in self.graph.predecessors(topic_node):
                pred_data = self.graph.nodes[predecessor]
                if pred_data.get("type") == "faculty":
                    edge_data = self.graph[predecessor][topic_node]
                    weight = edge_data.get("weight", 0)
                    faculty_weights[predecessor] = faculty_weights.get(predecessor, 0) + weight
        
        # Format results
        for faculty_id, weight in faculty_weights.items():
            faculty_data = self.graph.nodes[faculty_id]
            experts.append({
                "id": faculty_id,
                "name": faculty_data.get("name", ""),
                "department": faculty_data.get("department", ""),
                "expertise_weight": weight,
            })
        
        return sorted(experts, key=lambda x: x["expertise_weight"], reverse=True)[:top_k]
    
    def get_faculty_papers(self, faculty_id: str) -> List[Dict]:
        """Get all papers authored by a faculty member."""
        papers = []
        
        for successor in self.graph.successors(faculty_id):
            if self.graph.nodes[successor].get("type") == "paper":
                paper_data = self.graph.nodes[successor]
                papers.append({
                    "id": successor,
                    "title": paper_data.get("title", ""),
                    "year": paper_data.get("year", ""),
                    "authors": paper_data.get("authors", []),
                })
        
        return sorted(papers, key=lambda x: x.get("year", ""), reverse=True)
    
    def find_research_clusters(self, min_size: int = 3) -> List[Dict]:
        """Find research clusters using community detection."""
        from networkx.algorithms import community
        
        # Use only faculty and collaboration edges
        collab_graph = nx.Graph()
        
        for u, v, data in self.graph.edges(data=True):
            if data.get("type") == "collaborates_with":
                collab_graph.add_edge(u, v, weight=data.get("weight", 1))
        
        if collab_graph.number_of_nodes() == 0:
            return []
        
       # Louvain community detection
        communities = community.louvain_communities(collab_graph, weight="weight")
        
        clusters = []
        for i, comm in enumerate(communities):
            if len(comm) >= min_size:
                members = []
                for node_id in comm:
                    node_data = self.graph.nodes[node_id]
                    members.append({
                        "id": node_id,
                        "name": node_data.get("name", ""),
                    })
                
                clusters.append({
                    "cluster_id": i,
                    "size": len(comm),
                    "members": members,
                })
        
        return sorted(clusters, key=lambda x: x["size"], reverse=True)
