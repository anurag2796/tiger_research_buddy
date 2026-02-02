"""Google Scholar crawler for faculty publications."""

import json
import time
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config import DATA_DIR

console = Console()

# Try to import scholarly, handle if not installed
try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    console.print("[yellow]scholarly not installed. Google Scholar features limited.[/]")


class ScholarCrawler:
    """Crawler for Google Scholar professor profiles."""
    
    def __init__(self, use_proxy: bool = False):
        self.use_proxy = use_proxy
        self._setup_scholarly()
    
    def _setup_scholarly(self):
        """Configure scholarly with optional proxy."""
        if not SCHOLARLY_AVAILABLE:
            return
            
        if self.use_proxy:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                console.print("[green]✓ Using proxy for Google Scholar[/]")
            except Exception as e:
                console.print(f"[yellow]Proxy setup failed: {e}. Using direct connection.[/]")

    def search_author(self, name: str, affiliation: str = "RIT") -> Optional[dict]:
        """Search for an author on Google Scholar."""
        if not SCHOLARLY_AVAILABLE:
            return None
            
        try:
            # Search with affiliation filter
            query = f"{name} {affiliation}"
            search_query = scholarly.search_author(query)
            
            # Get first result
            author = next(search_query, None)
            if author:
                return self._extract_author_info(author)
                
        except Exception as e:
            console.print(f"[yellow]Scholar search failed for {name}: {e}[/]")
        
        return None

    def _extract_author_info(self, author: dict) -> dict:
        """Extract relevant info from scholar author object."""
        try:
            # Fill in detailed information
            author = scholarly.fill(author)
            
            return {
                "name": author.get("name", ""),
                "affiliation": author.get("affiliation", ""),
                "email_domain": author.get("email_domain", ""),
                "interests": author.get("interests", []),
                "citations": author.get("citedby", 0),
                "h_index": author.get("hindex", 0),
                "i10_index": author.get("i10index", 0),
                "publications": self._get_publications(author, limit=10)
            }
        except Exception as e:
            console.print(f"[yellow]Could not fill author details: {e}[/]")
            return {
                "name": author.get("name", ""),
                "interests": author.get("interests", []),
                "citations": 0,
                "publications": []
            }

    def _get_publications(self, author: dict, limit: int = 10) -> list[dict]:
        """Extract top publications from author."""
        publications = []
        
        pubs = author.get("publications", [])[:limit]
        for pub in pubs:
            try:
                publications.append({
                    "title": pub.get("bib", {}).get("title", ""),
                    "year": pub.get("bib", {}).get("pub_year", ""),
                    "citations": pub.get("num_citations", 0),
                    "venue": pub.get("bib", {}).get("venue", "")
                })
            except Exception:
                continue
        
        return publications

    def enrich_faculty_data(self, faculty: list[dict], delay: float = 5.0) -> list[dict]:
        """Add Google Scholar data to faculty list."""
        if not SCHOLARLY_AVAILABLE:
            console.print("[yellow]Skipping Scholar enrichment (scholarly not available)[/]")
            return faculty
        
        console.print("[bold blue]📚 Fetching Google Scholar data...[/]")
        console.print("[dim]This may take a while due to rate limiting...[/]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                "Searching scholars...",
                total=len(faculty)
            )
            
            for prof in faculty:
                name = prof.get("name", "")
                if name:
                    scholar_data = self.search_author(name)
                    if scholar_data:
                        prof["scholar"] = scholar_data
                    
                    # Rate limiting to avoid blocks
                    time.sleep(delay)
                
                progress.advance(task)
        
        return faculty

    def save_scholar_data(self, data: list[dict], filename: str = "scholar_data.json") -> Path:
        """Save scholar data to file."""
        filepath = DATA_DIR / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓ Saved scholar data to {filepath}[/]")
        return filepath


def enrich_with_scholar(faculty: list[dict]) -> list[dict]:
    """Convenience function to enrich faculty with scholar data."""
    crawler = ScholarCrawler()
    return crawler.enrich_faculty_data(faculty)
