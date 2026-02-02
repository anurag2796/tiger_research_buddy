"""RAG (Retrieval Augmented Generation) engine for the chatbot."""

from typing import Optional

from rich.console import Console

from ..database.vector_store import get_vector_store, VectorStore
from .gemini_client import get_gemini_client, GeminiClient

console = Console()

# System prompt for the chatbot
SYSTEM_PROMPT = """You are TigerResearchBuddy 🐅, an AI assistant helping RIT students explore research opportunities in the Golisano College of Computing and Information Sciences.

Your role is to:
1. Help students find professors whose research aligns with their interests
2. Explain research areas available at RIT Computing
3. Provide information about publications and expertise
4. Guide students on how to approach professors for research opportunities

Guidelines:
- Be friendly, encouraging, and supportive
- If you don't have specific information, say so honestly
- Suggest related topics or professors when exact matches aren't found
- Encourage students to visit professor websites and read their publications
- Always provide URLs when available

Remember: You're helping students find their passion in computing research!"""


class RAGEngine:
    """RAG pipeline combining vector search with Gemini generation."""
    
    def __init__(
        self, 
        vector_store: Optional[VectorStore] = None,
        gemini_client: Optional[GeminiClient] = None
    ):
        self.vector_store = vector_store or get_vector_store()
        self.gemini_client = gemini_client or get_gemini_client()
        self.conversation_history: list[dict] = []
    
    def initialize(self):
        """Initialize both vector store and Gemini client."""
        self.vector_store.initialize()
        self.gemini_client.initialize()
    
    def query(self, user_query: str, n_results: int = 5) -> str:
        """Process a user query using RAG."""
        # Step 1: Retrieve relevant documents
        results = self.vector_store.search(user_query, n_results=n_results)
        
        # Step 2: Build context from results
        context = self._build_context(results)
        
        # Step 3: Generate response with Gemini
        response = self.gemini_client.generate(
            prompt=user_query,
            context=context,
            system_prompt=SYSTEM_PROMPT
        )
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_query})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def _build_context(self, results: list[dict]) -> str:
        """Build context string from search results."""
        if not results:
            return "No specific information found in the database."
        
        context_parts = ["Relevant information from RIT Computing:"]
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            doc_type = metadata.get("doc_type", "unknown")
            
            context_parts.append(f"\n--- Result {i} ({doc_type}) ---")
            context_parts.append(content)
            
            if metadata.get("url"):
                context_parts.append(f"URL: {metadata['url']}")
        
        return "\n".join(context_parts)
    
    def search_only(self, query: str, n_results: int = 5) -> list[dict]:
        """Perform semantic search without generation."""
        return self.vector_store.search(query, n_results=n_results)
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        console.print("[dim]Conversation history cleared[/]")
    
    def get_history(self) -> list[dict]:
        """Get conversation history."""
        return self.conversation_history


# Global instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get the global RAG engine instance."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
