
import sys
import os
import time
from pathlib import Path
from rich.console import Console

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.crawlers.scholar_crawler import ScholarCrawler

def main():
    console = Console()
    console.print("[bold]Testing Scholar Crawler Integration...[/]")
    
    # 1. Setup
    # Note: Running with 2 threads to test concurrency without heavy load
    crawler = ScholarCrawler(max_workers=2)
    
    # 2. Dummy Data - includes a name variation to test resolution
    faculty = [
        {"name": "Christopher Kanan", "department": "Computer Science"},
        {"name": "Matt Huenerfauth", "department": "Information Sciences"},
        {"name": "C. Kanan", "department": "Golisano College"} # Should resolve to same as Christopher
    ]
    
    # 3. Run Enrichment
    console.print("[dim]Starting enrichment...[/]")
    start_time = time.time()
    enriched = crawler.enrich_faculty_data(faculty)
    duration = time.time() - start_time
    
    console.print(f"\n[green]Enrichment took {duration:.2f}s[/]")
    
    # 4. Verify
    for prof in enriched:
        console.print(f"\n[bold]Name: {prof['name']}[/]")
        console.print(f"Canonical ID: {prof.get('id', 'N/A')}")
        if 'scholar' in prof:
            console.print(f"[blue]Scholar Data Found: {prof['scholar'].get('name')}[/]")
            console.print(f"  Citations: {prof['scholar'].get('citations')}")
            console.print(f"  Publications: {len(prof['scholar'].get('publications', []))}")
            if prof.get('scholar'):
                 console.print(f"  Top Pub: {prof['scholar'].get('publications')[0]['title'] if prof['scholar'].get('publications') else 'None'}")
        else:
            console.print("[red]No Scholar Data found (might be rate limited or not found)[/]")

if __name__ == "__main__":
    main()
