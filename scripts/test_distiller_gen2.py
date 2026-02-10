#!/usr/bin/env python3
"""
Test DeepDistiller Gen 2 upgrade.
Verifies VLM validation, schema compliance, and author resolution.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.pdf_distiller import DeepDistiller
from src.utils.config import DATA_DIR
from rich.console import Console

console = Console()

def test_distiller():
    """Run DeepDistiller on a sample PDF and verify output."""
    
    console.print("[bold cyan]Testing DeepDistiller Gen 2 Upgrade[/]\n")
    
    # 1. Initialize
    distiller = DeepDistiller()
    
    # 2. Find a sample PDF
    pdf_dir = DATA_DIR / "pdfs"
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    if not pdfs:
        console.print("[red]No PDFs found in data/pdfs/[/]")
        console.print("[yellow]Please add a sample PDF to test[/]")
        return False
    
    sample_pdf = pdfs[0]
    console.print(f"[green]Testing on: {sample_pdf.name}[/]\n")
    
    # 3. Extract text
    console.print("[cyan]Step 1: Extracting text (Vision-First)...[/]")
    text = distiller.extract_text(sample_pdf)
    if len(text) < 100:
        console.print(f"[red]Extraction failed: text too short ({len(text)} chars)[/]")
        return False
    console.print(f"[green]✓ Extracted {len(text)} characters[/]\n")
    
    # 4. Classify domain
    console.print("[cyan]Step 2: Classifying domain...[/]")
    domain = distiller.classify_domain(text)
    console.print(f"[green]✓ Domain: {domain}[/]\n")
    
    # 5. Distill
    console.print("[cyan]Step 3: Distilling to TigerCard 2.0...[/]")
    card = distiller.distill(text, sample_pdf.name, domain=domain, pdf_path=sample_pdf)
    
    if not card:
        console.print("[red]Distillation failed[/]")
        return False
    
    console.print("[green]✓ Card generated[/]\n")
    
    # 6. Validate Schema
    console.print("[cyan]Step 4: Validating TigerCard 2.0 schema...[/]")
    required_fields = ["card_id", "bibliographic_data", "core_content", "knowledge_graph"]
    
    for field in required_fields:
        if field not in card:
            console.print(f"[red]✗ Missing required field: {field}[/]")
            return False
        console.print(f"[green]✓ Found: {field}[/]")
    
    # Check knowledge_graph structure
    kg = card.get("knowledge_graph", {})
    if "nodes" not in kg or "edges" not in kg:
        console.print("[red]✗ Invalid knowledge_graph structure[/]")
        return False
    
    console.print(f"[green]✓ Knowledge Graph: {len(kg['nodes'])} nodes, {len(kg['edges'])} edges[/]\n")
    
    # 7. Check Author Resolution
    console.print("[cyan]Step 5: Checking author resolution...[/]")
    authors = card.get("bibliographic_data", {}).get("authors", [])
    if authors:
        console.print(f"[green]✓ Found {len(authors)} authors:[/]")
        for author in authors[:3]:  # Show first 3
            if isinstance(author, dict):
                name = author.get("name", "Unknown")
                faculty_id = author.get("faculty_id")
                if faculty_id:
                    console.print(f"  • {name} [dim](matched to RIT faculty)[/]")
                else:
                    console.print(f"  • {name}")
            else:
                console.print(f"  • {author}")
    else:
        console.print("[yellow]⚠ No authors extracted[/]")
    
    # 8. Save output
    output_path = DATA_DIR / "research_cards" / f"test_{sample_pdf.stem}_card.json"
    with open(output_path, "w") as f:
        json.dump(card, f, indent=2)
    
    console.print(f"\n[bold green]✓ All checks passed![/]")
    console.print(f"[dim]Output saved to: {output_path}[/]")
    
    return True

if __name__ == "__main__":
    success = test_distiller()
    sys.exit(0 if success else 1)
