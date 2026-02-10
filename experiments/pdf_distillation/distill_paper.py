import sys
import os
import json
import time
from pathlib import Path

# Add parent directory to path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.chatbot.ollama_client import OllamaClient
from rich.console import Console
from rich.panel import Panel

console = Console()

# Test configuration
TEST_PDF = "yuri_towards_responsible_ai_a_design_space_exploration_of_human-c.pdf"
PDF_DIR = Path("data/pdfs")

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        # Read the first 10 pages (enough for a deep summary of most papers)
        for page in doc[:10]:
            text += page.get_text() + "\n"
        return text
    except ImportError:
        console.print("[red]PyMuPDF not installed. Run 'pip install pymupdf'[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/]")
        return ""

def distill_research_card(text: str) -> dict:
    """Use Qwen to distill a structured Research Card."""
    client = OllamaClient()
    client.initialize()

    schema = {
        "title": "Paper Title",
        "core_problem": "What specific problem does this paper solve?",
        "methodology": "Brief description of the proposed method/approach",
        "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
        "novelty": "What is the primary contribution?",
        "entities": {
            "datasets": ["List", "of", "datasets"],
            "models": ["List", "of", "models"],
            "metrics": ["List", "of", "metrics"]
        }
    }

    # Truncate text to fit context window (approx 20k chars is safe for 32k context)
    # qwen2.5:32b has 32k context, so we can be generous
    truncated_text = text[:25000]

    prompt = f"""
    You are a Senior Research Scientist.
    Read the following research paper text and distill it into a high-density 'Research Card' JSON.
    
    Target Schema:
    {json.dumps(schema, indent=2)}

    Rules:
    1. Output ONLY valid JSON.
    2. Be concise but specific (density is key).
    3. Extract specific entity names (e.g., 'ResNet-50', 'CIFAR-10') not generic terms.

    --- PAPER TEXT START ---
    {truncated_text}
    --- PAPER TEXT END ---
    """

    console.print("[bold cyan]🧠 Distilling Research Card (this may take a minute)...[/]")
    start_time = time.time()
    response = client.generate(prompt, system_prompt="You are a Scientific Knowledge Distillation Engine.")
    duration = time.time() - start_time
    
    console.print(f"[dim]Generation took {duration:.2f}s[/]")

    # Naive JSON cleaning
    try:
        json_str = response.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
             json_str = json_str.split("```")[1].split("```")[0]
        
        return json.loads(json_str)
    except Exception as e:
        console.print(f"[red]JSON parsing failed: {e}[/]")
        console.print(response[:500] + "...")
        return None

def main():
    console.print(Panel("[bold purple]⚗️ Experiment 3: PDF Deep Distillation[/]"))

    pdf_path = PDF_DIR / TEST_PDF
    if not pdf_path.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/]")
        return

    # 1. Extraction
    console.print(f"[dim]Reading {TEST_PDF}...[/]")
    text = extract_text_from_pdf(pdf_path)
    if not text: return
    console.print(f"[green]✓ Extracted {len(text)} characters[/]")

    # 2. Distillation
    card = distill_research_card(text)

    if card:
        console.print("\n[bold green]✅ Research Card Generated:[/]")
        console.print(json.dumps(card, indent=2))
    
        # Save check
        with open("experiments/pdf_distillation/sample_card.json", "w") as f:
            json.dump(card, f, indent=2)
            
if __name__ == "__main__":
    main()
