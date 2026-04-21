"""RAG (Retrieval Augmented Generation) engine for the chatbot."""

from typing import Optional

from rich.console import Console

from ..database.vector_store import get_vector_store, VectorStore
from ..retrieval.hybrid_retriever import HybridRetriever
from .gemini_client import get_gemini_client, GeminiClient
from .ollama_client import get_ollama_client, OllamaClient
from .response_postprocessor import get_postprocessor
from ..utils.db_logger import setup_db_logging, generate_trace_id

console = Console()
logger = setup_db_logging("RAGEngine")

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
        self.ollama_client = get_ollama_client()
        self.hybrid_retriever = HybridRetriever(self.vector_store) # Initialize hybrid retriever
        self.conversation_history: list[dict] = []
    
    
    def initialize(self):
        """Initialize vector store, Gemini client, and load skills."""
        self.vector_store.initialize()
        self.gemini_client.initialize()
        try:
            self.ollama_client.initialize()
        except Exception as e:
            logger.error(f"Ollama client init warning: {e}")
            console.print(f"[yellow]Ollama client init warning: {e}[/]")
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
            logger.error(f"Could not load skills.md: {e}")
            console.print(f"[yellow]Could not load skills.md: {e}[/]")
        return DEFAULT_SYSTEM_PROMPT

    
    def query(self, user_query: str, n_results: int = 5) -> str:
        """Process a user query using RAG."""
        trace_id = generate_trace_id()
        logger.info(f"Processing RAG query: {user_query} (Trace ID: {trace_id})")
        
        # Step 2: Advanced RAG - Query Expansion & Context
        search_query = self._expand_query(user_query)
        
        # Step 3: Retrieve relevant documents using Hybrid Search
        results = self.hybrid_retriever.hybrid_search(search_query, k=n_results * 2) # Get more to allow filtering
        
        current_threshold = 0.65  # General threshold
            
        # Filter results by distance if they came from vector search (distances are usually smaller for better matches in Chroma)
        # Note: HybridRetriever now returns docs with 'rrf_score'. Higher is better. 
        # We can either filter on rrf_score or distance if available.
        # RRF scores are typically small (e.g., 0.01-0.03 range), so we just take the top-N directly.
        filtered_results = results[:n_results]
        
        console.print(f"[dim]Hybrid Search retrieved {len(results)} chunks, kept top {len(filtered_results)}[/]")
        
        # Step 4: Build context from refined results
        context = self._build_context(filtered_results)
        
        # If no relevant context found after filtering
        if not filtered_results:
             fallback_msg = "I don't have specific information about that in my database. I recommend checking the RIT Computing website or contacting the department."
             self.conversation_history.append({"role": "user", "content": user_query})
             self.conversation_history.append({"role": "assistant", "content": fallback_msg})
             return fallback_msg
             
        # Inject conversation history into query
        history_prefix = ""
        if self.conversation_history:
            history_str = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in self.conversation_history[-10:]  # Keep last 5 turns (max length 10)
            )
            history_prefix = f"\n--- Conversation History ---\n{history_str}\n--- End History ---\n\n"
        
        full_prompt = f"{history_prefix}Current Query: {user_query}"
        
        # Step 5: Generate response with LLM
        try:
            raw_response = self.gemini_client.generate(
                prompt=full_prompt,
                context=context,
                system_prompt=self.system_prompt
            )
            if raw_response.startswith("Sorry, I encountered an error:"):
                raise Exception(raw_response)
        except Exception as e:
            logger.warning(f"Gemini API failed or errored: {e}. Falling back to Ollama.")
            console.print(f"[yellow]Gemini API failed limit checks. Falling back to Ollama...[/]")
            try:
                raw_response = self.ollama_client.generate(
                    prompt=full_prompt,
                    context=context,
                    system_prompt=self.system_prompt
                )
            except Exception as ollama_e:
                logger.error(f"Ollama generation also failed: {ollama_e}")
                raw_response = "I encountered an error generating the response. Please try again."
        
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
        
        from ..utils.hardware import HW_PROFILE
        # A rough heuristic: 1 token ≈ 4 characters
        max_chars = HW_PROFILE.context_window * 3
        current_chars = 0

        context_parts = ["Relevant information from RIT Computing:"]
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            doc_type = metadata.get("doc_type", "unknown")
            
            part_lines = []
            part_lines.append(f"\n--- Result {i} ({doc_type}) ---")
            part_lines.append(content)
            
            # Add metadata fields to context so LLM sees them
            if metadata.get("email"):
                part_lines.append(f"Email: {metadata['email']}")
            if metadata.get("office"):
                part_lines.append(f"Office: {metadata['office']}")
            if metadata.get("department"):
                part_lines.append(f"Department: {metadata['department']}")
            if metadata.get("phone"):
                part_lines.append(f"Phone: {metadata['phone']}")
            
            if metadata.get("url"):
                part_lines.append(f"URL: {metadata['url']}")

            part_text = "\n".join(part_lines)

            if current_chars + len(part_text) > max_chars:
                logger.warning(f"Context truncated at result {i} to respect HW_PROFILE.context_window")
                console.print(f"[yellow]Context truncated to fit in context window ({HW_PROFILE.context_window} tokens)[/yellow]")
                break

            context_parts.append(part_text)
            current_chars += len(part_text)
        
        return "\n".join(context_parts)
    
    def search_only(self, query: str, n_results: int = 5) -> list[dict]:
        """Perform semantic search without generation."""
        return self.hybrid_retriever.hybrid_search(query, k=n_results)
    
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
