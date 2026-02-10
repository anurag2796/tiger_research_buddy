
import time
import os
from pathlib import Path
from rich.console import Console
from rich.progress import (
    Progress, 
    BarColumn, 
    TextColumn, 
    TimeRemainingColumn, 
    TaskID, 
    TimeElapsedColumn, 
    SpinnerColumn
)

console = Console()
DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "pdfs"
CARDS_DIR = DATA_DIR / "research_cards"

def monitor():
    console.print("[bold cyan]🐅 TigerStack Ingestion Monitor[/]")
    
    # Get total target
    pdfs = list(PDF_DIR.glob("*.pdf"))
    total_files = len(pdfs)
    
    if total_files == 0:
        console.print("[red]No PDFs found in data/pdfs![/]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TextColumn("[bold green]{task.completed}/{task.total} Cards"),
        "•",
        TimeElapsedColumn(),
        "•",
        TextColumn("[bold cyan]ETA:"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Distilling Knowledge Graph...", total=total_files)
        
        while not progress.finished:
            # Count completed cards
            cards = len(list(CARDS_DIR.glob("*.json")))
            progress.update(task, completed=cards)
            
            if cards >= total_files:
                break
                
            time.sleep(1)
            
    console.print("\n[bold green]✨ Ingestion Complete![/]")

if __name__ == "__main__":
    monitor()
