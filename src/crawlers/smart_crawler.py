import re
import json
import time
import asyncio
import aiohttp
import aiofiles
from urllib.parse import urljoin, urlparse
from typing import Set, Dict, List, Optional
import networkx as nx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..utils.config import CrawlConfig, RESTRICTED_CONFIG, LLMConfig
from ..utils.db_logger import setup_db_logging, log_timing, PerformanceTimer as Timer
from ..chatbot.ollama_client import OllamaClient

logger = setup_db_logging("SmartCrawler")

console = Console()

class SmartCrawler:
    """
    v2 Crawler for TigerResearchBuddy (Async Implementation).
    
    Features:
    1. AsyncIO: Concurrent crawling for speed.
    2. Checkpointing: Resumes from where it left off.
    3. Resilience: Retries on network failure.
    4. Graph-based Traversal: Tracks site structure.
    5. LLM Extraction: Uses local LLM for data parsing.
    """
    
    def __init__(self, config: CrawlConfig = RESTRICTED_CONFIG):
        self.config = config
        self.base_url = config.START_URLS[0] # Primary entry point
        self.domain = urlparse(self.base_url).netloc
        self.concurrency = config.CONCURRENCY
        self.semaphore = asyncio.Semaphore(self.concurrency)
        
        # Site Graph to map structure
        self.site_graph = nx.DiGraph()
        
        # State
        self.visited: Set[str] = set()
        self.scraped_data: List[dict] = []
        self.queue: List[str] = []
        
        # LLM
        self.llm_client = OllamaClient(model=LLMConfig.PIPELINE_MODEL)
        
        # Checkpoint file
        self.checkpoint_file = config.CHECKPOINT_FILE
        
    def clean_html(self, html_content: str) -> str:
        """Strip HTML to core content for the LLM."""
        soup = BeautifulSoup(html_content, "lxml")
        
        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "meta", "noscript", "svg"]):
            tag.decompose()
            
        # Get text with strict separation
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n+', '\n', text)
        return text[:25000] # Increased context window for Nomic/Qwen to 8k context


    def extract_links(self, html_content: str, current_url: str) -> List[str]:
        """Extract valid internal links and update graph."""
        soup = BeautifulSoup(html_content, "lxml")
        links = []
        
        # Paths we care about for Computing college
        valid_paths = ["/computing/", "/directory/", "/people/", "/research/", "/faculty-staff"]
        
        for a in soup.find_all("a", href=True):
            href = a['href']
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)
            
            # Filter for internal domain links only
            if parsed.netloc == self.domain:
                # Basic filtering to avoid garbage (calendars, login, etc)
                if not any(x in full_url.lower() for x in ["login", "calendar", "event", "pdf", "jpg", "png", "news", "events"]):
                    # Strict path filtering to stay focused
                    if any(path in parsed.path for path in valid_paths):
                        links.append(full_url)
                        
                        # Add edge to graph (Current -> Found)
                        self.site_graph.add_edge(current_url, full_url)
                    
        return links

    async def extract_profile_data(self, url: str, text_content: str) -> Optional[dict]:
        """Use Qwen to extract profile JSON (Async wrapper)."""
        # ... (Rest of method is same, but I need to include it or carefully replace)
        # Using replace_file_content I must replace the exact block.
        # But this instruction is to update extract_links and process_url. 
        # I should use multi_replace.
        pass # Placeholder for actual tool call logic below

    @log_timing("Extract Profile Data")
    async def extract_profile_data(self, url: str, text_content: str) -> Optional[dict]:
        """Use Qwen to extract profile JSON (Async wrapper)."""
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
            # Run async LLM call
            response = await self.llm_client.generate_async(
                prompt, 
                system_prompt="You are a JSON extractor.", 
                options=LLMConfig.DEFAULT_OPTIONS
            )
            
            # Robust JSON Cleaning
            text = re.sub(r'```json\s*|\s*```', '', response).strip()
            
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
            if "Extra data" in str(e):
                 console.print(f"[yellow]JSON Parse Error for {url}[/]")
            return None

    @log_timing("Fetch Page")
    async def fetch_page(self, session, url: str) -> Optional[str]:
        """Fetch page content with retries."""
        retries = 3
        for i in range(retries):
            try:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        return None
            except Exception as e:
                if i == retries - 1:
                    logger.error(f"Failed to fetch {url}: {e}")
                    console.print(f"[red]Failed to fetch {url}: {e}[/]")
                await asyncio.sleep(1 * (i + 1)) # Exponential backoff
        return None

    async def process_url(self, session, url: str, progress, task_id):
        """Process a single URL."""
        start_time = time.perf_counter()
        async with self.semaphore:
            # Fetch
            with Timer(f"Fetching {url}", use_rich=False) as timer:
                html = await self.fetch_page(session, url)
            fetch_duration = timer.duration or 0

            if not html:
                console.print(f"[red]Failed to fetch content from {url} (took {fetch_duration:.2f}s)[/]")
                return

            console.print(f"[blue]Fetched {url} ({len(html)} bytes) in {fetch_duration:.2f}s[/]")
            clean_text = self.clean_html(html)
            
            # Extract Links
            new_links = self.extract_links(html, url)
            if new_links:
                console.print(f"[dim]Found {len(new_links)} links in {url}: {new_links[:3]}...[/]")
                
            for link in new_links:
                if link not in self.visited:
                    self.visited.add(link)
                    self.queue.append(link)
            
            # Analyze Profile
            if "/directory/" in url or "/people/" in url:
                with Timer(f"Extracting Profile {url}", use_rich=False) as timer:
                    data = await self.extract_profile_data(url, clean_text)
                extract_duration = timer.duration or 0
                
                if data:
                    self.scraped_data.append(data)
                    progress.advance(task_id)
                    console.print(f"[green]✓ Extracted: {data.get('name')} in {extract_duration:.2f}s[/]")
                    
            total_duration = time.perf_counter() - start_time
            logger.info(f"Processed {url} in {total_duration:.2f}s")
            console.print(f"[dim]Processed {url} in {total_duration:.2f}s[/]")
            
            await asyncio.sleep(self.config.CRAWL_DELAY) # Polite delay

    async def crawl(self):
        """Main async crawl loop."""
        url = self.base_url
        max_profiles = self.config.MAX_PROFILES
        
        # Load checkpoint if exists
        self.load_checkpoint()
        
        if not self.visited:
            self.queue.append(url)
            self.visited.add(url)
        
        console.print(f"[bold blue]🕷️ Starting Async SmartCrawl[/]")
        console.print(f"[dim]Concurrency: {self.concurrency} | Resuming: {len(self.scraped_data)} profiles[/]")
        
        profiles_found = len(self.scraped_data)
        
        async with aiohttp.ClientSession(headers={
            "User-Agent": "TigerResearchBuddy/2.1 (Async)"
        }) as session:
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total} profiles"),
                console=console
            ) as progress:
                # task = progress.add_task("Crawling...", total=max_profiles, completed=profiles_found)
                # Use infinite spinner for discovery phase?
                task = progress.add_task("Crawling...", total=max_profiles, completed=profiles_found)
                
                while self.queue and profiles_found < max_profiles:
                    # Get batch of URLs
                    batch_size = min(self.concurrency, len(self.queue))
                    batch = []
                    for _ in range(batch_size):
                        if self.queue:
                            batch.append(self.queue.pop(0))
                            
                    # Process batch concurrently
                    tasks = [self.process_url(session, u, progress, task) for u in batch]
                    await asyncio.gather(*tasks)
                    
                    # Update found count
                    profiles_found = len(self.scraped_data)
                    
                    # Periodic Checkpoint
                    if len(self.scraped_data) % 5 == 0:
                        self.save_checkpoint()

        self.save_data()
        self.save_graph()
        # Clean up checkpoint on success
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            
        return self.scraped_data

    def save_checkpoint(self):
        """Save current state to disk."""
        state = {
            "visited": list(self.visited),
            "queue": self.queue,
            "scraped_data": self.scraped_data
        }
        with open(self.checkpoint_file, "w") as f:
            json.dump(state, f)
            
    def load_checkpoint(self):
        """Load state from disk."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r") as f:
                    state = json.load(f)
                    self.visited = set(state.get("visited", []))
                    self.queue = state.get("queue", [])
                    self.scraped_data = state.get("scraped_data", [])
                console.print(f"[yellow]↺ Resumed from checkpoint: {len(self.visited)} pages visited[/]")
            except Exception as e:
                console.print(f"[red]Failed to load checkpoint: {e}[/]")

    def save_data(self):
        """Save extracted data to JSON."""
        path = self.config.OUTPUT_FILE
        with open(path, "w") as f:
            json.dump({"faculty": self.scraped_data}, f, indent=2)
        console.print(f"[bold green]💾 Saved {len(self.scraped_data)} profiles to {path}[/]")

    def save_graph(self):
        """Save the site link structure graph."""
        path = self.config.BASE_DIR / "site_graph.gml"
        nx.write_gml(self.site_graph, path)
        console.print(f"[bold green]🕸️ Saved Site Graph ({self.site_graph.number_of_nodes()} nodes) to {path}[/]")


def run_smart_crawl(start_url: Optional[str] = None, max_profiles: int = 10) -> List[dict]:
    """Synchronous wrapper to run the SmartCrawler."""
    crawler = SmartCrawler()
    if start_url:
        crawler.base_url = start_url
        crawler.config.START_URLS = [start_url]
    
    # Update max limit
    crawler.config.MAX_PROFILES = max_profiles
    
    return asyncio.run(crawler.crawl())

if __name__ == "__main__":
    run_smart_crawl()
