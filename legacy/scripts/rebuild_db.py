import sys
import os
sys.path.append(os.getcwd())

from src.database import load_data_to_vectorstore
from rich.console import Console

console = Console()

def rebuild():
    console.print("[bold blue]📦 Rebuilding Vector Store...[/]")
    try:
        # This function loads rit_data.json and re-indexes everything
        store = load_data_to_vectorstore()
        console.print("[green]✓ Rebuild complete![/]")
    except Exception as e:
        console.print(f"[red]Rebuild failed: {e}[/]")

if __name__ == "__main__":
    rebuild()
