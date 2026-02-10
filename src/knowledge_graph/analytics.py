"""Graph analytics for knowledge graph."""

import networkx as nx
from typing import Dict, List


class GraphAnalytics:
    """Analytics and metrics for the knowledge graph."""
    
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
    
    def get_influential_researchers(self, top_k: int = 10) -> List[Dict]:
        """Find most influential researchers using PageRank."""
        # Create subgraph with only faculty nodes
        faculty_nodes = [n for n, d in self.graph.nodes(data=True) 
                        if d.get("type") == "faculty"]
        
        if len(faculty_nodes) < 2:
            return []
        
        subgraph = self.graph.subgraph(faculty_nodes)
        
        try:
            pagerank = nx.pagerank(subgraph, weight="weight")
            
            results = []
            for node_id, score in sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:top_k]:
                node_data = self.graph.nodes[node_id]
                results.append({
                    "id": node_id,
                    "name": node_data.get("name", ""),
                    "influence_score": score,
                })
            
            return results
        except:
            return []
    
    def get_topic_distribution(self) -> Dict[str, int]:
        """Get distribution of research topics."""
        topic_counts = {}
        
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "topic":
                category = data.get("category", "other")
                topic_counts[category] = topic_counts.get(category, 0) + 1
        
        return dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True))
    
    def get_collaboration_strength(self, faculty1_id: str, faculty2_id: str) -> float:
        """Get collaboration strength between two faculty."""
        if self.graph.has_edge(faculty1_id, faculty2_id):
            return self.graph[faculty1_id][faculty2_id].get("weight", 0)
        return 0.0
    
    def find_shortest_research_path(self, faculty1_id: str, faculty2_id: str) -> List[str]:
        """Find shortest path between two faculty through research connections."""
        try:
            path = nx.shortest_path(self.graph.to_undirected(), faculty1_id, faculty2_id)
            return path
        except nx.NetworkXNoPath:
            return []
