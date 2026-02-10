"""Graph-enhanced query engine for intelligent chatbot responses."""

from typing import Dict, List, Optional, Tuple
from .ollama_client import get_ollama_client
from ..knowledge_graph.builder import build_knowledge_graph
from ..knowledge_graph.queries import GraphQueries
from ..knowledge_graph.analytics import GraphAnalytics
from ..knowledge_graph.data_mining import DataMining


class GraphEnhancedQueryEngine:
    """Enhanced query engine that combines vector search with knowledge graph."""
    
    def __init__(self):
        self.client = get_ollama_client()
        self.graph = None
        self.queries = None
        self.analytics = None
        self.data_mining = None
        self._initialize_graph()
    
    def _initialize_graph(self):
        """Load knowledge graph and initialize query interfaces."""
        try:
            self.graph = build_knowledge_graph()
            self.queries = GraphQueries(self.graph)
            self.analytics = GraphAnalytics(self.graph)
            self.data_mining = DataMining()
        except Exception as e:
            print(f"Warning: Could not initialize knowledge graph: {e}")
    
    def expand_query(self, query: str) -> str:
        """
        Uses LLM to generate related search terms.
        Example: "sustainable farming" -> "sustainable farming agriculture crop optimization"
        """
        if not self.client._initialized:
            self.client.initialize()
            
        prompt = f"""
        You are a research assistant.
        Given the user search query: "{query}"
        Generate 3-5 related academic keywords or concepts that would help find relevant research papers or faculty.
        Output ONLY the keywords separated by spaces. Do not explain.
        """
        
        # Heuristic: If query looks like a specific name search, don't expand or minimally expand
        if any(x in query.lower() for x in ["professor", "dr.", "prof", "who is", "email", "contact"]):
            # Just return original for specific entity lookups to avoid vector drift
            return query
            
        try:
            expansion = self.client.generate(prompt, system_prompt="You are a keyword generator.")
            # Simple cleaning
            expanded = f"{query} {expansion.strip()}"
            return expanded
        except Exception as e:
            print(f"Query expansion failed: {e}")
            return query
    
    def get_graph_insights(self, query: str) -> Dict[str, any]:
        """Extract insights from knowledge graph based on query."""
        if not self.graph:
            return {}
        
        insights = {}
        query_lower = query.lower()
        
        # Detect query intent
        is_asking_about_faculty = any(word in query_lower for word in ["who", "faculty", "professor", "researcher", "expert"])
        is_asking_about_topics = any(word in query_lower for word in ["research", "work on", "study", "topic"])
        is_asking_about_collaboration = any(word in query_lower for word in ["collaborate", "collaboration", "work with", "partner"])
        
        # Try to find mentioned faculty
        name_candidates = self._extract_names(query)
        for name in name_candidates:
            faculty_id = self.queries.find_faculty_by_name(name)
            if faculty_id:
                insights["faculty_id"] = faculty_id
                insights["faculty_expertise"] = self.queries.get_faculty_expertise(faculty_id)
                insights["faculty_papers"] = self.queries.get_faculty_papers(faculty_id)
                break
        
        # Find topics mentioned
        topics_found = []
        for topic in query_lower.split():
            if len(topic) > 3:  #Skip short words
                experts = self.queries.find_experts_in_topic(topic, top_k=5)
                if experts:
                    topics_found.append({
                        "topic": topic,
                        "experts": experts
                    })
        
        if topics_found:
            insights["topics"] = topics_found
        
        # Get research clusters if asking about collaborations
        if is_asking_about_collaboration:
            clusters = self.queries.find_research_clusters(min_size=2)
            if clusters:
                insights["research_clusters"] = clusters[:3]  # Top 3 clusters
        
        # Get influential researchers
        if is_asking_about_faculty or "influential" in query_lower or "leading" in query_lower:
            influencers = self.analytics.get_influential_researchers(top_k=5)
            if influencers:
                insights["influential_researchers"] = influencers
        
        return insights
    
    def get_data_mining_insights(self) -> Dict[str, any]:
        """Get general data mining insights (topics, patterns)."""
        if not self.data_mining:
            return {}
        
        insights = {}
        
        # Get discovered topics
        try:
            topics = self.data_mining.discover_topics_lda(n_topics=5, n_words=5)
            if topics:
                insights["research_themes"] = topics
        except:
            pass
        
        # Get key phrases
        try:
            phrases = self.data_mining.extract_key_phrases(top_k=10)
            if phrases:
                insights["key_research_areas"] = [phrase for phrase, score in phrases]
        except:
            pass
        
        return insights
    
    def enrich_context(self, query: str, vector_results: List[Dict]) -> str:
        """Enrich vector search results with graph insights."""
        graph_insights = self.get_graph_insights(query)
        
        enriched_context = ""
        
        # Add faculty expertise if found
        if "faculty_expertise" in graph_insights and graph_insights["faculty_expertise"]:
            enriched_context += "\n### Faculty Expertise:\n"
            for topic in graph_insights["faculty_expertise"][:5]:
                enriched_context += f"- {topic['topic']} (expertise level: {topic['weight']:.1f})\n"
        
        # Add papers if found
        if "faculty_papers" in graph_insights and graph_insights["faculty_papers"]:
            enriched_context += "\n### Recent Papers:\n"
            for paper in graph_insights["faculty_papers"][:3]:
                enriched_context += f"- {paper['title']} ({paper['year']})\n"
        
        # Add topic experts
        if "topics" in graph_insights:
            for topic_data in graph_insights["topics"][:2]:
                if topic_data["experts"]:
                    enriched_context += f"\n### Experts in {topic_data['topic']}:\n"
                    for expert in topic_data["experts"][:3]:
                        enriched_context += f"- {expert['name']} (expertise: {expert['expertise_weight']:.1f})\n"
        
        # Add research clusters for collaboration queries
        if "research_clusters" in graph_insights:
            enriched_context += "\n### Research Collaboration Groups:\n"
            for cluster in graph_insights["research_clusters"][:2]:
                members = ", ".join([m["name"] for m in cluster["members"][:3]])
                enriched_context += f"- Group with {cluster['size']} members: {members}\n"
        
        return enriched_context
    
    def _extract_names(self, text: str) -> List[str]:
        """Simple name extraction from text (looks for capitalized words)."""
        import re
        # Find sequences of capitalized words
        pattern = r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b'
        matches = re.findall(pattern, text)
        return [m for m in matches if len(m) > 3]  # Filter out short matches


# Backwards compatibility
class QueryEngine(GraphEnhancedQueryEngine):
    """Alias for backwards compatibility."""
    pass
