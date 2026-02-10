import re
import json
import time
from urllib.parse import urljoin, urlparse
from typing import Set, Dict, List, Optional
import networkx as nx
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..chatbot.ollama_client import OllamaClient
from ..utils.config import DATA_DIR

console = Console()

class SmartCrawler:
    """
    v2 Crawler for TigerResearchBuddy.
    
    Features:
    1. Graph-based Traversal (NetworkX): Tracks links and site structure.
    2. LLM Extraction (Qwen): Uses Qwen to parse unstructured HTML into JSON.
    3. Resilience: Robust to layout changes.
    """
    
    def __init__(self, base_url: str = "https://www.rit.edu/computing/directory"):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.session = requests.Session()
        self.session.headers.update({
             "User-Agent": "TigerResearchBuddy/2.0 (Academic Research Assistant)"
        })
        
        # Site Graph to map structure
        self.site_graph = nx.DiGraph()
        
        # State
        self.visited: Set[str] = set()
        self.scraped_data: List[dict] = []
        
        # LLM
        self.llm_client = OllamaClient()
        
    def clean_html(self, html_content: str) -> str:
        """Strip HTML to core content for the LLM."""
        soup = BeautifulSoup(html_content, "lxml")
        
        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "meta", "noscript", "svg"]):
            tag.decompose()
            
        # Get text with strict separation
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n+', '\n', text)
        return text[:10000] # Increased context window for Nomic/Qwen

    def extract_links(self, html_content: str, current_url: str) -> List[str]:
        """Extract valid internal links and update graph."""
        soup = BeautifulSoup(html_content, "lxml")
        links = []
        
        for a in soup.find_all("a", href=True):
            href = a['href']
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)
            
            # Filter for internal domain links only
            if parsed.netloc == self.domain and full_url not in self.visited:
                # Basic filtering to avoid garbage (calendars, login, etc)
                if not any(x in full_url.lower() for x in ["login", "calendar", "event", "pdf", "jpg", "png"]):
                    links.append(full_url)
                    
                    # Add edge to graph (Current -> Found)
                    self.site_graph.add_edge(current_url, full_url)
                    
        return links

    def extract_profile_data(self, url: str, text_content: str) -> Optional[dict]:
        """Use Qwen to extract profile JSON."""
        schema = {
            "name": "Full Name",
            "title": "Academic Title",
            "department": "Department Name",
            "email": "Email",
            "bio": "Professional Bio",
            "research_interests": ["List", "of", "interests"],
            "education": ["List", "of", "degrees"],
            "publications": ["List", "of", "recent publications (titles)"]
        }
        
        prompt = f"""
        You are a Data Extraction Engine.
        Extract faculty profile data from the text below into strictly valid JSON.
        
        Target Schema:
        {json.dumps(schema, indent=2)}
        
        Rules:
        1. Output ONLY valid JSON.
        2. If this is NOT a faculty profile (e.g. a directory listing or generic page), return null.
        3. Be precise.
        
        --- TEXT ---
        {text_content}
        --- END TEXT ---
        """
        
        try:
            # We assume initialize() is fast/idempotent
            self.llm_client.initialize() 
            response = self.llm_client.generate(prompt, system_prompt="You are a JSON extractor.")
            
            # Robust JSON Cleaning
            # 1. Strip Markdown
            text = re.sub(r'```json\s*|\s*```', '', response).strip()
            
            # 2. Find outer braces
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                data = json.loads(json_str)
                
                # Basic validation
                if data and data.get("name"):
                    data["url"] = url
                    return data
            
            return None
            
        except Exception as e:
            # Only print error if it's not a known "not a profile" null case
            if "Extra data" in str(e):
                 console.print(f"[yellow]JSON Parse Error for {url}[/]")
            return None

    def crawl_directory(self, start_url: str = None, max_profiles: int = 10):
        """Crawl the directory and extract profiles."""
        url = start_url or self.base_url
        queue = [url]
        self.visited.add(url)
        
        console.print(f"[bold blue]🕷️ Starting SmartCrawl at {url}[/]")
        console.print("[dim]Building Site Graph & Extracting Profiles...[/]")
        
        profiles_found = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} profiles"),
            console=console
        ) as progress:
            task = progress.add_task("Crawling...", total=max_profiles)
            
            while queue and profiles_found < max_profiles:
                current_url = queue.pop(0)
                
                try:
                    # 1. Fetch
                    # console.print(f"Fetching {current_url}...")
                    response = self.session.get(current_url, timeout=10)
                    if response.status_code != 200:
                        continue
                        
                    html = response.text
                    clean_text = self.clean_html(html)
                    
                    # 2. Extract Links (Graph Building)
                    new_links = self.extract_links(html, current_url)
                    for link in new_links:
                        if link not in self.visited:
                            self.visited.add(link)
                            queue.append(link)
                    
                    # 3. Analyze content (Is this a profile?)
                    # Heuristic: URL contains name-like pattern or specific path
                    if "/directory/" in current_url:
                        data = self.extract_profile_data(current_url, clean_text)
                        if data:
                            self.scraped_data.append(data)
                            profiles_found += 1
                            progress.advance(task)
                            console.print(f"[green]✓ Extracted: {data.get('name')}[/]")
                            
                    time.sleep(0.5) # Be polite
                    
                except Exception as e:
                    console.print(f"[yellow]Error parsing {current_url}: {e}[/]")

        self.save_data()
        self.save_graph()

    def save_data(self):
        """Save extracted data to JSON."""
        path = DATA_DIR / "rit_data_v2.json"
        with open(path, "w") as f:
            json.dump({"faculty": self.scraped_data}, f, indent=2)
        console.print(f"[bold green]💾 Saved {len(self.scraped_data)} profiles to {path}[/]")

    def save_graph(self):
        """Save the site link structure graph."""
        path = DATA_DIR / "site_graph.gml" # GML is good for NetworkX
        nx.write_gml(self.site_graph, path)
        console.print(f"[bold green]🕸️ Saved Site Graph ({self.site_graph.number_of_nodes()} nodes) to {path}[/]")

if __name__ == "__main__":
    # Test run
    crawler = SmartCrawler()
    # Start at directory root
    crawler.crawl_directory("https://www.rit.edu/computing/directory", max_profiles=3)
