"""Ollama client for offline TigerResearchBuddy chat.

Uses local LLM via Ollama - no internet required!
"""

from typing import Optional, Generator

from rich.console import Console

console = Console()

from ..utils.config import LLMConfig
from ..utils.hardware import HW_PROFILE

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
        
        self._async_lock = None
    
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
            import sys
            # X3 fix: platform-aware start command
            start_cmd = (
                "brew services start ollama"
                if sys.platform == "darwin"
                else "sudo systemctl start ollama"
            )
            raise RuntimeError(
                f"Ollama server not running. Start it with: {start_cmd}\nError: {e}"
            )

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
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response asynchronously (non-blocking) with proper cancellation support."""
        import asyncio
        from ollama import AsyncClient
        
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
            for key, val in LLMConfig.DEFAULT_OPTIONS.items():
                if key not in options:
                    options[key] = val
            kwargs["options"] = options

            # B3 fix: Semaphore limit is driven by HW_PROFILE.chat_concurrency
            # (env var OLLAMA_CHAT_CONCURRENCY, default 2 on macOS / 1 on Linux).
            # This prevents Orin VRAM panics while letting the M4 Max run 2 concurrent LLM calls.
            if self._async_lock is None:
                limit = HW_PROFILE.chat_concurrency
                self._async_lock = asyncio.Semaphore(limit)
                console.print(f"[dim]Ollama async semaphore: {limit} concurrent slot(s)[/]")
                
            async with self._async_lock:
                client = AsyncClient()
                response = await client.chat(
                    model=model or self.model,
                    messages=messages,
                    **kwargs
                )
                return response['message']['content']
        except asyncio.CancelledError:
            console.print("[yellow]Async generation cancelled by client disconnect.[/]")
            raise
        except Exception as e:
            console.print(f"[red]Ollama async error: {e}[/]")
            return f"Sorry, I encountered an error: {str(e)}"

    async def generate_stream_async(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        request=None,
        model: Optional[str] = None,
        **kwargs,
    ):
        """Async streaming generator with disconnect-aware VRAM release.

        Yields token chunks one at a time.  On each chunk the generator
        checks ``request.is_disconnected()`` (Starlette Request).  When
        the frontend aborts (AbortController), the loop breaks and the
        Ollama AsyncClient releases the GPU VRAM immediately — instead
        of completing a 15-45 s inference into the void.

        Parameters
        ----------
        request : starlette.requests.Request, optional
            If provided, the generator will poll for client disconnect.
        """
        import asyncio
        from ollama import AsyncClient

        if not self._initialized:
            self.initialize()

        # Build messages
        messages = []
        if not system_prompt:
            system_prompt = self._load_persona_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = ""
        if context:
            user_content += f"Context:\n{context}\n\n"
        user_content += prompt
        messages.append({"role": "user", "content": user_content})

        # Inject config defaults — apply every key from DEFAULT_OPTIONS unless caller overrides
        options = kwargs.pop("options", {})
        for key, val in LLMConfig.DEFAULT_OPTIONS.items():
            if key not in options:
                options[key] = val
        kwargs["options"] = options

        # Acquire VRAM semaphore
        if self._async_lock is None:
            limit = HW_PROFILE.chat_concurrency
            self._async_lock = asyncio.Semaphore(limit)
            console.print(f"[dim]Ollama stream semaphore: {limit} concurrent slot(s)[/]")

        try:
            async with self._async_lock:
                client = AsyncClient()
                stream = await client.chat(
                    model=model or self.model,
                    messages=messages,
                    stream=True,
                    **kwargs,
                )
                in_think = False
                think_buf = ""
                async for chunk in stream:
                    # Disconnect-aware: if the HTTP client aborted, stop
                    # inference immediately so Ollama frees the VRAM.
                    if request is not None and await request.is_disconnected():
                        console.print("[yellow]Client disconnected — aborting stream to free VRAM.[/]")
                        break

                    token = chunk.get("message", {}).get("content", "")
                    if not token:
                        continue

                    # Strip <think>...</think> blocks emitted by reasoning models
                    # (e.g. qwen3). Tokens may straddle tag boundaries so we use
                    # a small buffer to detect the closing tag.
                    if in_think:
                        think_buf += token
                        close = think_buf.find("</think>")
                        if close != -1:
                            in_think = False
                            remainder = think_buf[close + len("</think>"):]
                            think_buf = ""
                            if remainder.strip():
                                yield remainder
                    else:
                        combined = think_buf + token
                        think_buf = ""
                        open_tag = combined.find("<think>")
                        if open_tag != -1:
                            before = combined[:open_tag]
                            if before:
                                yield before
                            in_think = True
                            think_buf = combined[open_tag + len("<think>"):]
                            # Check if </think> already present in same token
                            close = think_buf.find("</think>")
                            if close != -1:
                                in_think = False
                                remainder = think_buf[close + len("</think>"):]
                                think_buf = ""
                                if remainder.strip():
                                    yield remainder
                        else:
                            yield combined
        except asyncio.CancelledError:
            console.print("[yellow]Stream cancelled by client disconnect.[/]")
            return
        except Exception as e:
            console.print(f"[red]Ollama stream error: {e}[/]")
            yield f"\n\n⚠️ Error: {str(e)}"

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
            if "temperature" not in options:
                options["temperature"] = LLMConfig.TEMPERATURE
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


# Global instance — Fix 5: thread-safe double-checked locking
import threading

_ollama_client: Optional[OllamaClient] = None
_ollama_client_lock = threading.Lock()


def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance (thread-safe)."""
    global _ollama_client
    if _ollama_client is None:
        with _ollama_client_lock:
            if _ollama_client is None:
                _ollama_client = OllamaClient()
    return _ollama_client
