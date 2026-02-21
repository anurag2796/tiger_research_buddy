"""Ollama client for offline TigerResearchBuddy chat.

Uses local LLM via Ollama - no internet required!
"""

from typing import Optional, Generator

from rich.console import Console

console = Console()

from ..utils.config import LLMConfig

# Default model - lightweight and fast
DEFAULT_MODEL = LLMConfig.CHAT_MODEL

# Check if ollama is available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    console.print("[yellow]Warning: ollama not installed. Run 'pip install ollama'[/]")


class OllamaClient:
    """Client for interacting with local Ollama LLM."""
    
    def __init__(self, model: str = DEFAULT_MODEL, persona: str = "tiger"):
        self.model = model
        self.persona = persona
        self._initialized = False
        self._available_models = []
        self._persona_prompts = {}
    
    def set_persona(self, persona: str):
        """Change the active persona (tiger, analyzer, critique)."""
        if persona not in ["tiger", "analyzer", "critique"]:
            raise ValueError(f"Unknown persona: {persona}")
        self.persona = persona
        console.print(f"[cyan]Switched to {persona} persona[/]")
    
    def initialize(self):
        """Initialize the Ollama client."""
        if self._initialized:
            return
        
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama library not installed. Run: pip install ollama")
        
        # Check if Ollama server is running
        try:
            models_response = ollama.list()
            
            # Handle ListResponse object (newer ollama library)
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict):
                models_list = models_response.get('models', [])
            else:
                models_list = []
            
            # Extract model names from Model objects
            self._available_models = []
            for m in models_list:
                if hasattr(m, 'model'):
                    self._available_models.append(m.model)
                elif isinstance(m, dict):
                    self._available_models.append(m.get('name', m.get('model', '')))
                elif isinstance(m, str):
                    self._available_models.append(m)
            
            if not self._available_models:
                console.print("[yellow]No models found. Pull a model first:[/]")
                console.print(f"[dim]Run: ollama pull {self.model}[/]")
            else:
                console.print(f"[green]✓ Ollama ready ({len(self._available_models)} models available)[/]")
                
                # Use first available model if default not found
                model_matches = [m for m in self._available_models if self.model in m]
                if model_matches:
                    self.model = model_matches[0]
                elif self._available_models:
                    self.model = self._available_models[0]
                console.print(f"[dim]Using model: {self.model}[/]")
            
            self._initialized = True
            
        except Exception as e:
            raise RuntimeError(f"Ollama server not running. Start it with: brew services start ollama\nError: {e}")

    def _load_persona_prompt(self) -> str:
        """Load the prompt for the current persona."""
        from pathlib import Path
        
        # Cache prompts
        if self.persona in self._persona_prompts:
            return self._persona_prompts[self.persona]
        
        # Map persona to file
        persona_files = {
            "tiger": "role.md",
            "analyzer": "analyzer.md",
            "critique": "critique.md"
        }
        
        prompt_file = Path("data/prompts") / persona_files.get(self.persona, "role.md")
        
        try:
            with open(prompt_file, "r") as f:
                prompt = f.read()
                self._persona_prompts[self.persona] = prompt
                return prompt
        except FileNotFoundError:
            console.print(f"[yellow]Warning: {prompt_file} not found, using default[/]")
            return "You are a helpful research assistant."



    
    async def generate_async(
        self, 
        prompt: str, 
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response asynchronously (non-blocking)."""
        import asyncio
        if not self._initialized:
            self.initialize()
            
        return await asyncio.to_thread(
            self.generate,
            prompt=prompt,
            context=context,
            system_prompt=system_prompt,
            **kwargs
        )

    def generate(
        self, 
        prompt: str, 
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from local LLM."""
        if not self._initialized:
            self.initialize()
        
        # Build the full prompt
        messages = []
        
        # Use persona-specific prompt if no custom system_prompt
        if not system_prompt:
            system_prompt = self._load_persona_prompt()
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        user_content = ""
        if context:
            user_content += f"Context:\n{context}\n\n"
        user_content += prompt
        
        messages.append({"role": "user", "content": user_content})
        
        try:
            # Set default options if not provided
            options = kwargs.get("options", {})
            if "num_ctx" not in options:
                options["num_ctx"] = LLMConfig.CONTEXT_WINDOW
            kwargs["options"] = options
            
            response = ollama.chat(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response['message']['content']
        except Exception as e:
            console.print(f"[red]Ollama error: {e}[/]")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def generate_stream(
        self, 
        prompt: str, 
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Stream a response from local LLM."""
        if not self._initialized:
            self.initialize()
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        user_content = ""
        if context:
            user_content += f"Context:\n{context}\n\n"
        user_content += prompt
        
        messages.append({"role": "user", "content": user_content})
        
        try:
            stream = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True
            )
            for chunk in stream:
                yield chunk['message']['content']
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def chat(self, messages: list[dict]) -> str:
        """Have a multi-turn conversation."""
        if not self._initialized:
            self.initialize()
        
        # Convert message format if needed
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            ollama_messages.append({"role": role, "content": content})
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=ollama_messages
            )
            return response['message']['content']
        except Exception as e:
            console.print(f"[red]Ollama chat error: {e}[/]")
            return f"Sorry, I encountered an error: {str(e)}"


def test_ollama() -> bool:
    """Test the Ollama connection."""
    try:
        client = OllamaClient()
        client.initialize()
        response = client.generate("Say 'Hello, TigerResearchBuddy!' briefly.")
        console.print(f"[green]✓ Ollama test successful: {response[:50]}...[/]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Ollama test failed: {e}[/]")
        return False


# Global instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
