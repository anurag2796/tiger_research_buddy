from typing import List, Dict
from ..database import get_vector_store, VectorStore
from ..database.models import Idea

class IdeaMatcher:
    """Matches ideas with potential collaborators and related research."""
    
    def __init__(self):
        self.store = get_vector_store()
        
    def find_collaborators(self, idea_text: str, n_results: int = 5) -> List[Dict]:
        """Find faculty members whose research matches the idea."""
        # Search specifically for professors
        results = self.store.search(
            query=idea_text, 
            n_results=n_results, 
            doc_type="professor"
        )
        return results

    def find_related_ideas(self, idea_text: str, n_results: int = 3) -> List[Dict]:
        """Find other similar ideas."""
        results = self.store.search(
            query=idea_text, 
            n_results=n_results, 
            doc_type="idea"
        )
        return results
    
    def match_idea(self, idea: Idea) -> Dict:
        """Run full matching for a new idea."""
        query = f"{idea.title} {idea.description} {', '.join(idea.tags)}"
        
        return {
            "collaborators": self.find_collaborators(query),
            "related_ideas": self.find_related_ideas(query)
        }
