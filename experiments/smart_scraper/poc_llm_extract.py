import sys
import os
import json
import re
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel

# Add parent directory to path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.chatbot.ollama_client import OllamaClient

console = Console()

def clean_html(html_content: str) -> str:
    """Convert HTML to cleaner text/markdown for the LLM."""
    soup = BeautifulSoup(html_content, "lxml")
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "meta", "noscript"]):
        script.decompose()
        
    # Get text with strict separation
    text = soup.get_text(separator="\n", strip=True)
    
    # Simple markdown conversion (h1, h2, h3)
    text = re.sub(r'\n+', '\n', text)  # Collapse newlines
    
    return text[:6000]  # Limit context for speed/context window

def extract_with_llm(text_content: str):
    """Ask Qwen to extract structured data."""
    client = OllamaClient()
    client.initialize()
    
    schema = {
        "name": "Full Name",
        "title": "Job Title / Position",
        "department": "Department Name",
        "email": "Email Address",
        "bio": "Brief professional bio (summary)",
        "research_interests": ["List", "of", "interests"],
        "education": ["List", "of", "degrees"]
    }
    
    prompt = f"""
    You are a Data Extraction Agent. 
    Analyze the following unstructured text from a professor's profile page and extract the data into a JSON object.
    
    Target JSON Schema:
    {json.dumps(schema, indent=2)}
    
    Rules:
    1. Output ONLY valid JSON. No markdown, no pre-amble.
    2. If a field is not found, use null.
    3. Be precise with names and titles.
    4. For 'bio', summarize the main professional description if it's too long.
    
    --- START PROFILE TEXT ---
    {text_content}
    --- END PROFILE TEXT ---
    """
    
    console.print("[bold cyan]🤖 Sending to Qwen...[/]")
    response = client.generate(prompt, system_prompt="You are a JSON-only data extraction engine.")
    
    # Clean response (remove markdown code blocks if any)
    json_str = re.sub(r'```json\s*|\s*```', '', response).strip()
    
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError:
        console.print("[red]Failed to parse JSON response[/]")
        console.print(response)
        return None

def main():
    console.print(Panel("[bold blue]🧪 Smart Scraper PoC: Qwen Extraction[/]"))
    
    html_path = "experiments/smart_scraper/test_profile.html"
    
    if not os.path.exists(html_path):
        console.print(f"[red]File not found: {html_path}[/]")
        return
        
    with open(html_path, "r") as f:
        html = f.read()
        
    # 1. Preprocess
    clean_text = clean_html(html)
    console.print(f"[dim]Preprocessed text ({len(clean_text)} chars)[/]")
    # console.print(clean_text[:500] + "...")
    
    # 2. Extract
    data = extract_with_llm(clean_text)
    
    if data:
        console.print("\n[bold green]✅ Extraction Successful![/]")
        console.print(json.dumps(data, indent=2))
        
        # Validation Check
        console.print("\n[bold]Validation:[/]")
        if "Kinsman" in data.get("name", ""):
            console.print("[green]✓ Name Match[/]")
        if "Computer Science" in data.get("department", ""):
            console.print("[green]✓ Department Match[/]")
        if data.get("research_interests"):
            console.print(f"[green]✓ Found {len(data['research_interests'])} interests[/]")
    
if __name__ == "__main__":
    main()
