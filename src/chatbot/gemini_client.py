"""Gemini API client for TigerResearchBuddy."""

from typing import Optional

from rich.console import Console

from ..utils.config import GEMINI_API_KEY, GEMINI_MODEL, validate_config

console = Console()

# Lazy import
_genai = None


def _get_genai():
    """Lazy load google.generativeai."""
    global _genai
    if _genai is None:
        import google.generativeai as genai
        _genai = genai
    return _genai


class GeminiClient:
    """Client for interacting with Gemini API."""
    
    def __init__(self):
        self.model = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the Gemini client."""
        if self._initialized:
            return
        
        validate_config()
        
        genai = _get_genai()
        genai.configure(api_key=GEMINI_API_KEY)
        
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self._initialized = True
        console.print(f"[green]✓ Gemini client initialized ({GEMINI_MODEL})[/]")
    
    def generate(
        self, 
        prompt: str, 
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response from Gemini."""
        if not self._initialized:
            self.initialize()
        
        # Build the full prompt
        full_prompt = ""
        
        if system_prompt:
            full_prompt += f"{system_prompt}\n\n"
        
        if context:
            full_prompt += f"Context:\n{context}\n\n"
        
        full_prompt += f"User Query: {prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            console.print(f"[red]Gemini API error: {e}[/]")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def chat(self, messages: list[dict]) -> str:
        """Have a multi-turn conversation."""
        if not self._initialized:
            self.initialize()
        
        try:
            chat = self.model.start_chat(history=[])
            
            # Replay conversation history
            for msg in messages[:-1]:
                if msg["role"] == "user":
                    chat.send_message(msg["content"])
            
            # Send final message and get response
            response = chat.send_message(messages[-1]["content"])
            return response.text
            
        except Exception as e:
            console.print(f"[red]Gemini chat error: {e}[/]")
            return f"Sorry, I encountered an error: {str(e)}"


def test_connection() -> bool:
    """Test the Gemini API connection."""
    try:
        client = GeminiClient()
        client.initialize()
        response = client.generate("Say 'Hello, TigerResearchBuddy!' briefly.")
        console.print(f"[green]✓ API test successful: {response[:50]}...[/]")
        return True
    except Exception as e:
        console.print(f"[red]✗ API test failed: {e}[/]")
        return False


# Global instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get the global Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
