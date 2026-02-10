import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))  # Ensure src is in path

from src.processors.pdf_distiller import DeepDistiller
from rich.console import Console

console = Console()

def test_integration():
    console.print("[cyan]Testing DeepDistiller + VisionCrawler Integration...[/]")
    
    # Initialize Distiller
    distiller = DeepDistiller()
    
    # Check if VisionCrawler is initialized
    if hasattr(distiller, 'vision_crawler'):
        console.print("[green]✓ VisionCrawler initialized in DeepDistiller[/]")
    else:
        console.print("[red]✗ VisionCrawler NOT found in DeepDistiller[/]")
        return
        
    # Test on a PDF
    pdf_dir = Path("data/pdfs")
    test_pdf = next(pdf_dir.glob("*.pdf"), None)
    
    if not test_pdf:
        console.print("[red]No PDFs found.[/]")
        return
        
    console.print(f"[yellow]Extracting text from {test_pdf.name}...[/]")
    
    # Run extraction
    text = distiller.extract_text(test_pdf)
    
    # Basic Validation
    if not text:
        console.print("[red]Extraction failed (empty text).[/]")
    elif len(text) < 100:
        console.print("[red]Extraction suspicious (too short).[/]")
    elif "# " in text: # Markdown header characteristic
        console.print("[green]✓ Output contains Markdown headers (# ) indicating Marker-PDF usage.[/]")
        console.print(f"[dim]Preview:\n{text[:200]}[/]")
    else:
        console.print("[yellow]Output might be plain text (PyMuPDF behavior?)[/]")
        console.print(f"[dim]Preview:\n{text[:200]}[/]")
        
    # Test Domain Classification
    console.print(f"[cyan]Classifying Domain for {test_pdf.name}...[/]")
    domain = distiller.classify_domain(text)
    console.print(f"[bold green]Domain Classified: {domain}[/]")
    
    # Test Distillation (TigerCard 2.0)
    console.print("[cyan]Running Distillation with TigerCard 2.0 Schema...[/]")
    card = distiller.distill(text, test_pdf.name, domain=domain)
    
    if card:
        console.print("[green]✓ Distillation Successful[/]")
        console.print(f"Title: {card.get('bibliographic_data', {}).get('title')}")
        console.print(f"Domain: {card.get('bibliographic_data', {}).get('primary_domain')}")
        
        kg = card.get('knowledge_graph', {})
        nodes = kg.get('nodes', [])
        edges = kg.get('edges', [])
        console.print(f"[bold]Knowledge Graph:[/bold] {len(nodes)} Nodes, {len(edges)} Edges")
        
        if nodes:
            console.print(f"Sample Node: {nodes[0]}")
    else:
        console.print("[red]Distillation Failed[/]")

if __name__ == "__main__":
    test_integration()
