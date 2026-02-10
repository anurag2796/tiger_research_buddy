"""Test persona switching in OllamaClient."""
from src.chatbot.ollama_client import OllamaClient
from rich.console import Console

console = Console()

def test_persona_switching():
    console.print("\n[bold blue]🧪 Testing Persona Switching...[/]")
    
    client = OllamaClient()
    
    # Test 1: Tiger (default)
    console.print("\n[bold]Test 1: Tiger Persona (Default)[/]")
    console.print(f"Current persona: {client.persona}")
    prompt_tiger = client._load_persona_prompt()
    console.print(f"Loaded prompt length: {len(prompt_tiger)} chars")
    assert "Tiger" in prompt_tiger or "buddy" in prompt_tiger.lower(), "Tiger persona not loaded"
    
    # Test 2: Switch to Analyzer
    console.print("\n[bold]Test 2: Analyzer Persona[/]")
    client.set_persona("analyzer")
    assert client.persona == "analyzer"
    prompt_analyzer = client._load_persona_prompt()
    console.print(f"Loaded prompt length: {len(prompt_analyzer)} chars")
    assert "Analyzer" in prompt_analyzer or "analytical" in prompt_analyzer.lower(), "Analyzer persona not loaded"
    
    # Test 3: Switch to Critique
    console.print("\n[bold]Test 3: Critique Persona[/]")
    client.set_persona("critique")
    assert client.persona == "critique"
    prompt_critique = client._load_persona_prompt()
    console.print(f"Loaded prompt length: {len(prompt_critique)} chars")
    assert "critique" in prompt_critique.lower() or "critical" in prompt_critique.lower(), "Critique persona not loaded"
    
    # Test 4: Caching
    console.print("\n[bold]Test 4: Prompt Caching[/]")
    prompt_critique_2 = client._load_persona_prompt()
    assert prompt_critique == prompt_critique_2, "Caching failed"
    console.print("[green]✓ All persona tests passed![/]")

if __name__ == "__main__":
    test_persona_switching()
