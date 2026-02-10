#!/usr/bin/env python3
"""
Test DeepDistiller Gen 2 on the Okutan paper (cyber attacks forecasting).
This is the paper critiqued in the evaluation report.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.pdf_distiller import DeepDistiller
from rich.console import Console

console = Console()

def test_okutan_paper():
    """Test on the specific Okutan paper."""
    
    pdf_path = Path("/Users/anurag/codebase/personalProjects/tiger_research_buddy/data/pdfs/ahmet_forecasting_cyber_attacks_with_imbalanced_data_sets_and_diff.pdf")
    
    if not pdf_path.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/]")
        return False
    
    console.print("[bold cyan]Testing on Okutan et al. Paper[/]\n")
    console.print("[dim]'Forecasting Cyber Attacks with Imbalanced Data Sets and Different Time Granularities'[/]\n")
    
    # Initialize distiller
    distiller = DeepDistiller()
    
    # Extract
    console.print("[cyan]1. Extracting text (Vision-First)...[/]")
    text = distiller.extract_text(pdf_path)
    console.print(f"[green]✓ Extracted {len(text)} characters[/]\n")
    
    # Classify
    console.print("[cyan]2. Classifying domain...[/]")
    domain = distiller.classify_domain(text)
    console.print(f"[green]✓ Domain: {domain}[/]\n")
    
    # Distill with VLM validation
    console.print("[cyan]3. Distilling with VLM validation enabled...[/]")
    card = distiller.distill(text, pdf_path.name, domain=domain, pdf_path=pdf_path)
    
    if not card:
        console.print("[red]Distillation failed[/]")
        return False
    
    console.print("[green]✓ Card generated[/]\n")
    
    # Save
    output_path = Path("data/research_cards/okutan_test_card.json")
    with open(output_path, "w") as f:
        json.dump(card, f, indent=2)
    
    console.print(f"[bold green]✓ Complete![/]")
    console.print(f"[dim]Saved to: {output_path}[/]\n")
    
    # Show key sections
    console.print("[bold]Key Extractions:[/]")
    console.print(f"  Title: {card.get('bibliographic_data', {}).get('title', 'N/A')}")
    console.print(f"  Authors: {len(card.get('bibliographic_data', {}).get('authors', []))}")
    console.print(f"  Nodes: {len(card.get('knowledge_graph', {}).get('nodes', []))}")
    console.print(f"  Edges: {len(card.get('knowledge_graph', {}).get('edges', []))}")
    
    return True

if __name__ == "__main__":
    success = test_okutan_paper()
    sys.exit(0 if success else 1)
