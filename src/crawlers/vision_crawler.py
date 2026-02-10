from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from rich.console import Console
import time

console = Console()

class VisionCrawler:
    """
    Prototype VLM-based Crawler/Parser using Marker-PDF.
    Replaces PyMuPDF heuristic extraction with Vision-based Model.
    """
    
    def __init__(self):
        console.print("[cyan]Initializing VisionCrawler (Marker-PDF)...[/]")
        start = time.time()
        # Load models
        # Note: minimal setup for Mac M-series (MPS)
        self.artifact_dict = create_model_dict()
        self.config = {
            "output_format": "markdown",
            "use_llm": False 
        }
        self.converter = PdfConverter(
            artifact_dict=self.artifact_dict,
            config=self.config
        )
        console.print(f"[green]Models loaded in {time.time() - start:.2f}s[/]")

    def convert_pdf(self, pdf_path: str, output_path: str = None) -> str:
        """
        Convert a single PDF to Markdown.
        """
        fpath = Path(pdf_path)
        if not fpath.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        console.print(f"[yellow]Processing {fpath.name}...[/]")
        start_time = time.time()
        
        # Run Marker conversion
        # The converter is callable directly on the file path
        rendered = self.converter(str(fpath))
        
        duration = time.time() - start_time
        console.print(f"[green]Converted to Markdown in {duration:.2f}s[/]")
        
        # Save output if requested
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(rendered.markdown, encoding='utf-8')
            console.print(f"[dim]Saved to {output_path}[/]")
            
        return rendered.markdown

if __name__ == "__main__":
    # Test on a dummy PDF if available, or create one?
    # For now, we'll checking for any PDF in data/pdfs
    import sys
    
    crawler = VisionCrawler()
    
    # Try to find a PDF to test
    pdf_dir = Path("data/pdfs")
    test_pdf = next(pdf_dir.glob("*.pdf"), None)
    
    if test_pdf:
        crawler.convert_pdf(str(test_pdf), output_path="experiments/marker_test.md")
    else:
        console.print("[red]No PDFs found in data/pdfs to test.[/]")
