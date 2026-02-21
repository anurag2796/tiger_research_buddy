import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def main():
    console.print(Panel("🚀 TigerResearchBuddy Pipeline has migrated to [bold]Dagster[/]!", style="bold blue"))
    console.print("To run the pipeline with UI:")
    console.print("  [green]dagster dev -m src.pipeline[/]")
    console.print("\nTo run headlessly:")
    console.print("  [green]dagster job launch -m src.pipeline -j restricted_pipeline[/] (Default)")
    console.print("  [green]dagster job launch -m src.pipeline -j full_pipeline[/] (Full Data)")
    
    console.print("\n[dim]The legacy script is deprecated. Please use Dagster for orchestration.[/]")

if __name__ == "__main__":
    main()
