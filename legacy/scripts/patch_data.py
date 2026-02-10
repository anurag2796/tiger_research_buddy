import sys
import os
import json
sys.path.append(os.getcwd())

from src.crawlers.rit_crawler import RITCrawler
from src.utils.config import DATA_DIR
from rich.console import Console

console = Console()

def patch_kinsman():
    console.print("[bold blue]🔧 Patching data for Thomas Kinsman...[/]")
    
    crawler = RITCrawler()
    url = "https://www.rit.edu/computing/directory/thomask-thomas-kinsman"
    
    # 1. Crawl new data
    console.print(f"Crawling {url}...")
    new_data = crawler.crawl_faculty_profile(url)
    
    console.print("\n[green]New Data Extracted:[/]")
    console.print(json.dumps(new_data, indent=2))
    
    if not new_data.get("research_interests"):
        console.print("[red]WARNING: Still no research interests found![/]")
    if not new_data.get("title"):
        console.print("[red]WARNING: Still no title found![/]")

    # 2. Update JSON
    json_path = DATA_DIR / "rit_data.json"
    with open(json_path, "r") as f:
        data = json.load(f)
    
    updated = False
    for fac in data["faculty"]:
        if "Kinsman" in fac["name"]:
            # Explicitly clear potentially bad fields if not found in new data
            if "bio" not in new_data:
                fac["bio"] = ""
            if "department" not in new_data:
                fac["department"] = ""
                
            fac.update(new_data)
            updated = True
            console.print(f"[green]✓ Updated entry for {fac['name']}[/]")
            break
            
    if updated:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓ Saved to {json_path}[/]")
    else:
        console.print("[red]Could not find Thomas Kinsman in existing JSON[/]")

if __name__ == "__main__":
    patch_kinsman()
