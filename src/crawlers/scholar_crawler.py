"""Google Scholar crawler for faculty publications."""

import json
import time
import os
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

# Try to import SerpApi
try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    console.print("[yellow]google-search-results not installed. SerpApi features disabled.[/]")


class ScholarCrawler:
    """Crawler for Google Scholar professor profiles."""
    
    def __init__(self, use_proxy: bool = False):
        self.use_proxy = use_proxy
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self._setup_scholarly()
        
        if self.serpapi_key and SERPAPI_AVAILABLE:
            console.print("[green]✓ SerpApi key found. Using SerpApi for better reliability.[/]")
        elif not self.serpapi_key:
            console.print("[yellow]No SERPAPI_KEY found. Falling back to scholarly.[/]")
    
    def _setup_scholarly(self):
        """Configure scholarly with optional proxy."""
        if not SCHOLARLY_AVAILABLE:
            return
            
        if self.use_proxy and not self.serpapi_key:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                console.print("[green]✓ Using proxy for Google Scholar[/]")
            except Exception as e:
                console.print(f"[yellow]Proxy setup failed: {e}. Using direct connection.[/]")

    def search_author(self, name: str, affiliation: str = "RIT") -> Optional[dict]:
        """Search for an author on Google Scholar."""
        # Method 1: Try SerpApi first if available (preferred)
        if self.serpapi_key and SERPAPI_AVAILABLE:
            try:
                return self._search_author_serpapi(name, affiliation)
            except Exception as e:
                console.print(f"[red]SerpApi failed for {name}: {e}[/]")
                console.print("[yellow]Falling back to scholarly...[/]")
        
        # Method 2: Fallback to scholarly
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

    def _search_author_serpapi(self, name: str, affiliation: str) -> Optional[dict]:
        """Search author using SerpApi."""
        params = {
            "engine": "google_scholar_profiles",
            "mauthors": f"{name} {affiliation}",
            "api_key": self.serpapi_key
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        profiles = results.get("profiles", [])
        if not profiles:
            return None
            
        # Get detailed profile for the first match
        profile = profiles[0]
        author_id = profile.get("author_id")
        
        if not author_id:
            return None
            
        # Fetch detailed profile
        return self._get_author_details_serpapi(author_id)

    def _get_author_details_serpapi(self, author_id: str) -> dict:
        """Fetch detailed author info from SerpApi."""
        params = {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "api_key": self.serpapi_key
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        author = results.get("author", {})
        articles = results.get("articles", [])
        
        # Format publications
        publications = []
        for art in articles[:10]:  # Limit to 10
            publications.append({
                "title": art.get("title", ""),
                "year": art.get("year", ""),
                "citations": art.get("cited_by", {}).get("value", 0),
                "venue": art.get("publication", "")
            })
            
        return {
            "name": author.get("name", ""),
            "affiliation": author.get("affiliations", ""),
            "email_domain": author.get("email", ""),
            "interests": [i.get("title", "") for i in author.get("interests", [])],
            "citations": author.get("cited_by", {}).get("table", [{}])[0].get("citations", {}).get("all", 0),
            "h_index": author.get("cited_by", {}).get("table", [{}])[1].get("h_index", {}).get("all", 0),
            "i10_index": author.get("cited_by", {}).get("table", [{}])[2].get("i10_index", {}).get("all", 0),
            "publications": publications
        }

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
        if not SCHOLARLY_AVAILABLE and not (self.serpapi_key and SERPAPI_AVAILABLE):
            console.print("[yellow]Skipping Scholar enrichment (no tools available)[/]")
            return faculty
        
        console.print("[bold blue]📚 Fetching Google Scholar data...[/]")
        if not self.serpapi_key:
            console.print("[dim]Using scholarly (rate limited)...[/]")
        else:
            console.print("[dim]Using SerpApi...[/]")
        
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
                    
                    # Rate limiting (less needed for SerpApi but good practice)
                    if not self.serpapi_key:
                        time.sleep(delay)
                    else:
                        time.sleep(1) # Slower delay for SerpApi
                
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

