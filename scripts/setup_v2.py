import sys
import os
import json
from rich.console import Console
from rich.panel import Panel

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crawlers.smart_crawler import SmartCrawler
from src.database.lance_manager import LanceManager
from src.utils.config import DATA_DIR

console = Console()

def main():
    console.print(Panel.fit("[bold orange1]🐅 TigerStack 2.0 Setup[/]", border_style="orange1"))
    
    # 1. Crawl
    console.print("\n[bold cyan]Phase 1: Smart Crawl[/]")
    # For demo, limits to 5 profiles. In prod, remove limit.
    max_p = 5 
    crawler = SmartCrawler()
    crawler.crawl_directory(max_profiles=max_p)
    
    # 2. Load Data
    data_path = DATA_DIR / "rit_data_v2.json"
    if not data_path.exists():
        console.print("[red]No data found![/]")
        return
        
    with open(data_path, "r") as f:
        raw_data = json.load(f)
        
    faculty = raw_data.get("faculty", [])
    console.print(f"[green]Loaded {len(faculty)} profiles from JSON[/]")
    
    # 3. Index in LanceDB
    console.print("\n[bold cyan]Phase 2: Indexing in LanceDB[/]")
    db = LanceManager()
    db.initialize()
    
    documents = []
    for prof in faculty:
        # Prepare content for embedding (Rich semantic representation)
        content = f"""
        Professor: {prof.get('name')}
        Title: {prof.get('title')}
        Department: {prof.get('department')}
        Bio: {prof.get('bio')}
        Research Interests: {', '.join(prof.get('research_interests', []))}
        """
        
        meta = {
            "name": prof.get('name'),
            "url": prof.get("url"),
            "type": "faculty"
        }
        
        documents.append({
            "content": content.strip(),
            "metadata": meta,
            "id": f"prof_{prof.get('name').replace(' ', '_')}"
        })
        
    db.add_documents(documents)
    
    console.print(Panel.fit("[bold green]✅ Setup Complete! TigerStack 2.0 is online.[/]", border_style="green"))

if __name__ == "__main__":
    main()
