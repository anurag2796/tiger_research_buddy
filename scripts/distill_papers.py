import argparse
import sys
from pathlib import Path
from rich.console import Console

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.processors.pdf_distiller import DeepDistiller

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Distill research papers into TigerCards.")
    parser.add_argument("--pdf-dir", type=str, default="data/pdfs", help="Directory containing PDFs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of papers to process")
    parser.add_argument("--force", action="store_true", help="Force reprocessing of existing cards")
    
    args = parser.parse_args()
    
    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        console.print(f"[red]PDF directory not found: {pdf_dir}[/]")
        sys.exit(1)
        
    console.print(f"[bold blue]🚀 Starting Distillation Pipeline[/]")
    console.print(f"Source: {pdf_dir}")
    console.print(f"Engine: apple_fast (Vision-First)")
    
    try:
        distiller = DeepDistiller(pdf_dir=pdf_dir)
        
        # We need to expose a way to limit/force in process_all, or just iterate here.
        # DeepDistiller.process_all currently iterates all.
        # Let's modify process_all or just iterate here if we want fine control.
        # For now, we'll use process_all and rely on its internal check, 
        # but we might need to patch it to accept limit/force.
        
        # Actually, let's just instantiate and run. 
        # The current implementation of process_all doesn't take args.
        # We will modify DeepDistiller.process_all to accept these args in a follow-up if needed,
        # or just implement the loop here.
        
        # Implementing loop here for better control without changing class too much yet.
        pdfs = list(pdf_dir.glob("*.pdf"))
        if args.limit:
            pdfs = pdfs[:args.limit]
            
        console.print(f"[dim]Processing {len(pdfs)} papers...[/]")
        
        for pdf in pdfs:
            output_path = distiller.output_dir / f"{pdf.stem}_card.json"
            if output_path.exists() and not args.force:
                console.print(f"[dim]Skipping {pdf.name} (exists)[/]")
                continue
                
            console.print(f"\n[bold cyan]Processing {pdf.name}...[/]")
            text = distiller.extract_text(pdf)
            if not text:
                continue
                
            domain = distiller.classify_domain(text)
            card = distiller.distill(text, pdf.name, domain=domain, pdf_path=pdf)
            
            if card:
                with open(output_path, "w") as f:
                    import json
                    json.dump(card, f, indent=2)
                console.print(f"[green]✓ Saved TigerCard for {pdf.name}[/]")
            else:
                console.print(f"[red]✗ Failed to distill {pdf.name}[/]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Process interrupted.[/]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
