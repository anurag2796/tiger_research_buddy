import sys
import time
import random
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Ensure src is in path
sys.path.append(str(Path.cwd()))

from src.crawlers.vision_crawler import VisionCrawler

console = Console()

def run_benchmark(sample_size=5, output_dir="experiments/benchmark_results"):
    console.print(f"[bold cyan]🚀 Starting Vision Crawler Benchmark (Sample Size: {sample_size})[/]")
    
    # Setup paths
    pdf_dir = Path("data/pdfs")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Get PDFs
    all_pdfs = list(pdf_dir.glob("*.pdf"))
    if not all_pdfs:
        console.print("[red]No PDFs found in data/pdfs[/]")
        return
        
    # Filter for reasonable size (e.g. < 15 pages) for quick benchmark
    import fitz
    candidates = []
    
    console.print("[dim]Scanning PDFs for suitable candidates (< 15 pages)...[/]")
    for p in all_pdfs:
        try:
            with fitz.open(p) as doc:
                if len(doc) <= 15:
                    candidates.append(p)
        except:
            continue
            
    if not candidates:
        console.print("[yellow]No short PDFs found. Using random sample of all PDFs.[/]")
        candidates = all_pdfs
        
    # Sample PDFs
    sample = random.sample(candidates, min(sample_size, len(candidates)))
    
    # Initialize Crawler
    console.print("[dim]Initializing models...[/]")
    init_start = time.time()
    crawler = VisionCrawler()
    console.print(f"[dim]Initialization took {time.time() - init_start:.2f}s[/]")
    
    # Results Table
    table = Table(title="Vision Crawler Benchmark Results")
    table.add_column("Filename", style="cyan")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Page Rate (s/page)", justify="right") # Placeholder if we can't reliably get pages quickly without opening
    
    total_time = 0
    total_bytes = 0
    
    for pdf in sample:
        file_size_mb = pdf.stat().st_size / (1024 * 1024)
        console.print(f"Processing [bold]{pdf.name}[/] ({file_size_mb:.2f} MB)...")
        
        start_time = time.time()
        try:
            markdown = crawler.convert_pdf(str(pdf), output_path=str(out_path / f"{pdf.stem}.md"))
            duration = time.time() - start_time
            
            # Simple page estimation (Marker doesn't return page count easily in simple API, 
            # but we can infer from logs or just leave it blank for now. 
            # Actually, `convert_pdf` in my prototype returns the markdown string.
            # I'll rely on time/file for now.)
            
            table.add_row(
                pdf.name[:40] + "..." if len(pdf.name) > 40 else pdf.name,
                f"{file_size_mb:.2f}",
                f"{duration:.2f}",
                "N/A"
            )
            
            total_time += duration
            total_bytes += pdf.stat().st_size
            
        except Exception as e:
            console.print(f"[red]Failed to process {pdf.name}: {e}[/]")
            table.add_row(pdf.name, "ERROR", "ERROR", "ERROR")
            
    console.print("\n")
    console.print(table)
    
    avg_time = total_time / len(sample)
    console.print(f"\n[bold green]Total Time:[/]{total_time:.2f}s")
    console.print(f"[bold green]Average Time per Paper:[/]{avg_time:.2f}s")
    console.print(f"[bold green]Estimated Time for 1,145 Papers:[/]{(avg_time * 1145) / 3600:.2f} hours")

if __name__ == "__main__":
    run_benchmark()
