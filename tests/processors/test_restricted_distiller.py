import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import asyncio
import os
import sys
from pathlib import Path
from rich.console import Console

# Ensure src is in the python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.processors.pdf_distiller import DeepDistiller
from src.utils.config import RESTRICTED_CONFIG

console = Console()

async def run_restricted_distillation_mock():
    """
    Simulate the 'Restricted Mode' segment-wise test for vector store/indexing stage
    by isolating the DeepDistiller logic which previously crashed due to the
    PyTorch 'Cannot copy out of meta tensor' bug.
    """
    console.print("\n[bold green]=== Starting Segment-Wise Test for Restricted Mode ===[/]")
    
    # Isolate one of the PDFs that previously failed
    project_root = Path(__file__).resolve().parent.parent
    pdf_dir = project_root / "data" / "pdfs"
    specific_pdf = pdf_dir / "connor_language_models_as_emotional_classifiers_for_textual_convers.pdf"
    
    if not specific_pdf.exists():
        console.print(f"[red]Error:[/red] The test PDF does not exist at {specific_pdf}. Cannot proceed.")
        # Fallback to the first available PDF in restricted mode
        restricted_pdfs = list(pdf_dir.glob("*.pdf"))
        if not restricted_pdfs:
             console.print("[red]Critical:[/red] No PDFs found in data/pdfs. Exiting.")
             return
        specific_pdf = restricted_pdfs[0]
        console.print(f"[yellow]Falling back to:[/yellow] {specific_pdf.name}")

    # Set up DeepDistiller with restricted fake DB to simulate 'Restricted Mode' exactly
    faculty_db_path = project_root / "data" / "restricted" / "rit_data_restricted.json"
    
    console.print(f"Initializing DeepDistiller with PDF: {specific_pdf.name}")
    distiller = DeepDistiller(pdf_dir=pdf_dir, faculty_db_path=faculty_db_path)
    
    console.print("\n[cyan]Executing extract_text_async()...[/]")
    try:
        # This is where the PyTorch bug (meta tensor) and GMFT string attribute bug occurs
        extracted_text = await distiller.extract_text_async(specific_pdf)
        
        if extracted_text:
            console.print(f"[bold green]✓ SUCCESS:[/bold green] Extracted {len(extracted_text)} characters without crashing.")
            console.print(f"Preview: {extracted_text[:200]}...")
        else:
            console.print("[yellow]⚠ WARNING:[/yellow] Extraction finished without crashing, but returned empty text.")
    except Exception as e:
        console.print(f"[bold red]❌ FAILED:[/bold red] Exception was raised during extraction:\n{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_restricted_distillation_mock())
