import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from src.processors.pdf_distiller import DeepDistiller
from rich.console import Console
import json
import time

console = Console()

# User Request: Ahmet's Paper
TARGET_PDF = "ahmet_forecasting_cyber_attacks_with_imbalanced_data_sets_and_diff.pdf"

def run_micro_pilot():
    distiller = DeepDistiller()
    # Override model to qwen2.5:32b for better JSON adherence
    distiller.llm_client.model = "qwen2.5:32b"
    
    pdf_dir = Path("data/pdfs")
    output_dir = Path("data/research_cards")
    
    console.print(f"[bold blue]🚀 Starting Micro Pilot on {TARGET_PDF}...[/]")
    
    pdf_path = pdf_dir / TARGET_PDF
    if not pdf_path.exists():
        console.print(f"[red]File not found: {TARGET_PDF}[/]")
        return

    start_time = time.time()

    # 1. Extract Text
    console.print(f"[cyan]1. Extracting Text (VisionCrawler)...[/]")
    text = distiller.extract_text(pdf_path)
    if not text:
        console.print(f"[red]Extraction Failed[/]")
        return
    console.print(f"[green]✓ Extracted {len(text)} characters in {time.time() - start_time:.2f}s[/]")
    
    # 2. Classify Domain
    console.print(f"[cyan]2. Classifying Domain...[/]")
    domain = distiller.classify_domain(text)
    console.print(f"[green]✓ Domain: {domain}[/]")
    
    # 3. Distill
    console.print(f"[cyan]3. Distilling TigerCard 2.0...[/]")
    card = distiller.distill(text, TARGET_PDF, domain=domain)
    
    if card:
        output_path = output_dir / f"{pdf_path.stem}_card.json"
        with open(output_path, "w") as f:
            json.dump(card, f, indent=2)
            
        kg = card.get('knowledge_graph', {})
        nodes = kg.get('nodes', [])
        console.print(f"[bold green]✓ Success! Saved to {output_path}[/]")
        console.print(f"Title: {card.get('bibliographic_data', {}).get('title')}")
        console.print(f"KG Nodes: {len(nodes)}")
        console.print(f"Sample Node: {nodes[0] if nodes else 'None'}")
    else:
        console.print(f"[red]✗ Distillation Failed[/]")

if __name__ == "__main__":
    run_micro_pilot()
