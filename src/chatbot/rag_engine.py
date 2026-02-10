"""RAG (Retrieval Augmented Generation) engine for the chatbot."""

from typing import Optional

from rich.console import Console

from ..database.vector_store import get_vector_store, VectorStore
from .gemini_client import get_gemini_client, GeminiClient
from .response_postprocessor import get_postprocessor
from .intent_classifier import get_intent_classifier, QueryIntent

console = Console()

# System prompt for the chatbot
# Default fallback prompt
DEFAULT_SYSTEM_PROMPT = """You are TigerResearchBuddy 🐅, an AI assistant helping RIT students explore research opportunities.
Be friendly, encouraging, and supportive. Use data from the retrieved context to answer questions.
IMPORTANT: You are ALLOWED and ENCOURAGED to share public faculty contact information (emails, office locations) found in the context to help students connect with professors."""




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
        """Initialize vector store, Gemini client, and load skills."""
        self.vector_store.initialize()
        self.gemini_client.initialize()
        self.system_prompt = self._load_system_prompt()
        console.print("[green]✓ RAG Engine initialized (Skills loaded)[/]")

    def _load_system_prompt(self) -> str:
        """Load system prompt from skills.md or use default."""
        from pathlib import Path
        skills_path = Path("data/prompts/skills.md")
        try:
            if skills_path.exists():
                return skills_path.read_text()
        except Exception as e:
            console.print(f"[yellow]Could not load skills.md: {e}[/]")
        return DEFAULT_SYSTEM_PROMPT

    
    def query(self, user_query: str, n_results: int = 5) -> str:
        """Process a user query using RAG with intent classification and post-processing."""
        
        # Step 0: Classify intent
        classifier = get_intent_classifier()
        intent, confidence = classifier.classify(user_query)
        console.print(f"[dim]Intent: {intent.value} (confidence: {confidence:.2f})[/]")
        
        # Step 1: Handle off-topic queries
        if classifier.should_refuse(intent):
            refusal_message = classifier.get_refusal_message()
            self.conversation_history.append({"role": "user", "content": user_query})
            self.conversation_history.append({"role": "assistant", "content": refusal_message})
            return refusal_message
        
        # Step 2: Advanced RAG - Query Expansion & Context
        search_query = self._expand_query(user_query)
        
        # Optimize n_results based on intent
        # Faculty lookup only needs top 1-2 usually, topic search might need more
        num_results = 3 if intent == QueryIntent.FACULTY_LOOKUP else n_results
        
        # Step 3: Retrieve relevant documents
        results = self.vector_store.search(search_query, n_results=num_results)
        
        # Determine dynamic threshold based on intent
        # Faculty lookup needs strict threshold to prevent hallucinations
        # Other queries (topic, contact) can be looser to find relevant context
        if intent == QueryIntent.FACULTY_LOOKUP:
            current_threshold = 0.52  # Strict: Only exact person matches
        else:
            current_threshold = 0.72  # Loose: Allow topic/contact context
            
        # Filter results by distance
        filtered_results = [
            r for r in results 
            if r.get('distance', 0) < current_threshold
        ]
        
        console.print(f"[dim]Retrieved {len(results)} chunks, kept {len(filtered_results)} after filtering (thresh={current_threshold})[/]")
        
        # Step 4: Build context from refined results
        context = self._build_context(filtered_results)
        
        # If no relevant context found after filtering, fallback immediately
        if not filtered_results and intent != QueryIntent.GENERAL_HELP:
             fallback_msg = "I don't have specific information about that in my database. I recommend checking the RIT Computing website or contacting the department."
             self.conversation_history.append({"role": "user", "content": user_query})
             self.conversation_history.append({"role": "assistant", "content": fallback_msg})
             return fallback_msg
        
        # Step 5: Generate response with LLM
        raw_response = self.gemini_client.generate(
            prompt=user_query,
            context=context,
            system_prompt=self.system_prompt
        )
        
        # Step 6: Post-process response to remove artifacts
        postprocessor = get_postprocessor()
        cleaned_response = postprocessor.process(raw_response)
        
        # Update conversation history with cleaned response
        self.conversation_history.append({"role": "user", "content": user_query})
        self.conversation_history.append({"role": "assistant", "content": cleaned_response})
        
        return cleaned_response
    
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
            
            # Add metadata fields to context so LLM sees them
            if metadata.get("email"):
                context_parts.append(f"Email: {metadata['email']}")
            if metadata.get("office"):
                context_parts.append(f"Office: {metadata['office']}")
            if metadata.get("department"):
                context_parts.append(f"Department: {metadata['department']}")
            if metadata.get("phone"):
                context_parts.append(f"Phone: {metadata['phone']}")
            
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

    def _expand_query(self, query: str) -> str:
        """Use LLM to expand query and resolve context."""
        # Simple heuristic for now: check if history exists and query is short
        # In a full implementation, we'd use the LLM to rewrite this.
        # For now, we'll append the last user query if this one is very short (likely a follow-up)
        
        expanded_query = query
        
        # Basic context awareness: If query contains "he", "she", "they", "it", append previous subject
        pronouns = ["he", "she", "they", "it", "him", "her", "his"]
        if any(p in query.lower().split() for p in pronouns) and self.conversation_history:
             # Find last assistant response to see who we were talking about
             last_msg = self.conversation_history[-1]
             if last_msg["role"] == "assistant":
                 # Heuristic: combine with previous user query for context
                 prev_user = self.conversation_history[-2]["content"] if len(self.conversation_history) >= 2 else ""
                 expanded_query = f"{prev_user} {query}"
                 console.print(f"[dim]Context awareness: Expanded to '{expanded_query}'[/]")
        
        return expanded_query


# Global instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get the global RAG engine instance."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
