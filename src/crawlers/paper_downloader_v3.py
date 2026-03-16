"""Enhanced paper downloader for TigerResearchBuddy.

Downloads research papers from:
- ArXiv (open access)
- Semantic Scholar API (metadata)
- Google Scholar links
- Direct PDF links

Respects rate limits and organizes downloads properly.
"""

import re
import time
import json
import hashlib
import threading
from pathlib import Path
from typing import Optional, Generator
from urllib.parse import urlparse, quote_plus

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.config import CrawlConfig, RESTRICTED_CONFIG
from ..utils.db_logger import setup_db_logging, log_timing, PerformanceTimer as Timer, generate_trace_id
from .vision_crawler import VisionCrawler

import time
from datetime import timedelta
from rich.table import Table
from rich.panel import Panel

logger = setup_db_logging("PaperDownloader")

console = Console()

# Rate limiting
RATE_LIMIT = 2.0  # seconds between requests

# Check if PyMuPDF is available
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PaperDownloader:
    """Download and process research papers."""
    
    def __init__(self, config: CrawlConfig = RESTRICTED_CONFIG):
        self.config = config
        self.pdf_dir = config.PDF_DIR
        self.papers_dir = config.PAPERS_DIR
        self.publications_dir = config.PUBLICATIONS_DIR
        
        self.session = requests.Session()
        
        # Connection pooling to avoid exhaustion
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=2)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            "User-Agent": "TigerResearchBuddy/1.0 (RIT Research Assistant; mailto:research@rit.edu)"
        })

        # ── Thread-safe counters ──────────────────────────────────────────
        self._lock = threading.Lock()
        self._counters = {
            "downloaded": 0,      # Unique PDFs actually fetched from network
            "cache_hits": 0,      # PDFs already on disk ("Already have")
            "failed": 0,          # Failed download attempts (final, after retries)
            "blacklisted_skips": 0,  # Skipped because URL is blacklisted
        }
        self._unique_papers: set = set()  # Track unique filenames for dedup metrics

        # ── Search result cache (thread-safe) ─────────────────────────────
        self._search_cache: dict = {}     # key=(query, source) -> results
        self._cache_lock = threading.Lock()

        # ── Per-API semaphores to prevent hammering ───────────────────────
        self._arxiv_sem = threading.Semaphore(2)     # Max 2 concurrent ArXiv calls
        self._ss_sem = threading.Semaphore(1)         # Serialize Semantic Scholar calls

        # ── Dead URL blacklist (persisted) ────────────────────────────────
        self._blacklist_path = config.BASE_DIR / "cache" / "dead_urls.json"
        self._blacklist_path.parent.mkdir(parents=True, exist_ok=True)
        self._blacklist: set = self._load_blacklist()

        # ── Download checkpoint (persisted) ───────────────────────────────
        self._checkpoint_path = config.BASE_DIR / "cache" / "download_checkpoint.json"
        self._processed_faculty: set = self._load_checkpoint()

        # ── Backward-compat properties ────────────────────────────────────
        # (Some callers may still read these directly)
        self.session.headers.update({
            "User-Agent": "TigerResearchBuddy/1.0 (RIT Research Assistant; mailto:research@rit.edu)"
        })
        self._counter_lock = threading.Lock()
        self._downloaded_count = 0
        self._failed_count = 0

        # Initialize Vision Crawler (lazy load will happen on first use, but we force it here for thread safety)
        engine = getattr(config, 'PDF_ENGINE', 'marker')
        self.vision_crawler = VisionCrawler(
            engine=engine,
            pdf_backend=getattr(config, 'PDF_BACKEND', 'pymupdf'),
            table_strategy=getattr(config, 'TABLE_STRATEGY', 'auto')
        )
        # Force load models in main thread to avoid MPS race conditions
        self.vision_crawler._load_models()

    @property
    def downloaded_count(self):
        with self._counter_lock:
            return self._downloaded_count

    @property
    def failed_count(self):
        with self._counter_lock:
            return self._failed_count

    def _inc_downloaded(self):
        with self._counter_lock:
            self._downloaded_count += 1

    def _inc_failed(self):
        with self._counter_lock:
            self._failed_count += 1

    # ─── Thread-safe helpers ──────────────────────────────────────────────────

    def _inc(self, key: str, n: int = 1):
        """Thread-safe counter increment."""
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + n

    def _get_counter(self, key: str) -> int:
        with self._lock:
            return self._counters.get(key, 0)

    def _load_blacklist(self) -> set:
        """Load persisted dead-URL blacklist."""
        if self._blacklist_path.exists():
            try:
                with open(self._blacklist_path) as f:
                    data = json.load(f)
                bl = set(data) if isinstance(data, list) else set()
                if bl:
                    console.print(f"[dim]Loaded {len(bl)} blacklisted URLs[/]")
                return bl
            except Exception:
                return set()
        return set()

    def _save_blacklist(self):
        """Persist dead-URL blacklist to disk."""
        with self._lock:
            urls = list(self._blacklist)
        with open(self._blacklist_path, "w") as f:
            json.dump(urls, f)

    def _blacklist_url(self, url: str):
        """Add a URL to the dead-URL blacklist (thread-safe)."""
        with self._lock:
            self._blacklist.add(url)
        # Persist periodically (every 10 additions)
        if len(self._blacklist) % 10 == 0:
            self._save_blacklist()

    def _is_blacklisted(self, url: str) -> bool:
        """Check if a URL is blacklisted."""
        with self._lock:
            return url in self._blacklist

    def _load_checkpoint(self) -> set:
        """Load set of already-processed faculty names."""
        if self._checkpoint_path.exists():
            try:
                with open(self._checkpoint_path) as f:
                    data = json.load(f)
                return set(data) if isinstance(data, list) else set()
            except Exception:
                return set()
        return set()

    def _save_checkpoint(self):
        """Persist processed faculty names."""
        with self._lock:
            names = list(self._processed_faculty)
        with open(self._checkpoint_path, "w") as f:
            json.dump(names, f)

    def _cached_search(self, query: str, source: str, search_fn, **kwargs) -> list:
        """Check cache before executing a search. Thread-safe."""
        cache_key = (query.lower().strip(), source)
        with self._cache_lock:
            if cache_key in self._search_cache:
                return self._search_cache[cache_key]
        # Cache miss — execute the actual search
        results = search_fn(query, **kwargs)
        with self._cache_lock:
            self._search_cache[cache_key] = results
        return results
    
    def _rate_limit(self, base_sleep: float = RATE_LIMIT):
        """Respect rate limits with adaptive backoff for 429 errors."""
        now = time.time()
        # If we recently hit a 429, wait until backoff expires
        backoff_until = getattr(self, '_backoff_until', 0)
        if now < backoff_until:
            wait = backoff_until - now
            logger.info(f"Rate limit backoff: waiting {wait:.1f}s")
            time.sleep(wait)
        else:
            time.sleep(base_sleep)

    def _handle_rate_limit_error(self):
        """Called after a 429 error — increase backoff exponentially."""
        current_backoff = getattr(self, '_current_backoff', RATE_LIMIT)
        # Exponential backoff: 3s → 6s → 12s → 24s → 48s, capped at 60s
        new_backoff = min(current_backoff * 2, 60.0)
        self._current_backoff = new_backoff
        self._backoff_until = time.time() + new_backoff
        logger.warning(f"429 detected — backing off for {new_backoff:.0f}s")
    
    def _get_safe_filename(self, title: str, author: str = "") -> str:
        """Generate a safe filename from title."""
        # Clean the title
        safe = re.sub(r'[^\w\s-]', '', title.lower())
        safe = re.sub(r'\s+', '_', safe)[:60]
        
        # Add author initial
        if author:
            author_init = author.split()[0].lower()[:10]
            safe = f"{author_init}_{safe}"
        
        return safe
    
    @log_timing("Search ArXiv")
    def search_arxiv(self, query: str, max_results: int = 10, is_author: bool = False) -> list[dict]:
        """Search ArXiv for papers."""
        logger.info(f"Searching ArXiv for: {query} (is_author={is_author})")
        console.print(f"[dim]Searching ArXiv for: {query}[/]")
        
        try:
            self._rate_limit()
            
            # Format query properly - ArXiv uses specific field prefixes
            if is_author:
                # Use full name for better precision (e.g. au:del_maestro)
                # Split by space and join with underscore if multiple parts
                parts = query.replace(",", "").split()
                if len(parts) > 1:
                     # "Tae Oh" -> "au:oh_t" or "au:tae_oh"? ArXiv standard is usually lastname_initial
                     # But full name search works reasonably well as "au:lastname_firstname"
                     # Let's try flexible search: au:lastname AND au:firstname
                     lastname = parts[-1]
                     firstname = parts[0]
                     search_query = f"au:{lastname}_{firstname}"
                else:
                    search_query = f"au:{query}"
            else:
                search_query = f"all:{quote_plus(query)}"
            
            url = f"http://export.arxiv.org/api/query?search_query={search_query}&max_results={max_results}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            
            papers = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                
                # Get PDF link
                pdf_link = None
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf':
                        pdf_link = link.get('href')
                        break
                
                # Get authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text)
                
                # Filter by Author Match (Client-side double check)
                if is_author:
                    # Check if query author is actually in list (fuzzy match)
                    # ArXiv search can be loose
                    query_lower = query.lower()
                    last_name = query_lower.split()[-1]
                    if not any(last_name in a.lower() for a in authors):
                         continue
                
                if title_elem is not None:
                    papers.append({
                        "title": title_elem.text.strip().replace('\n', ' '),
                        "abstract": summary_elem.text.strip() if summary_elem is not None else "",
                        "authors": authors,
                        "pdf_url": pdf_link,
                        "source": "arxiv"
                    })
            
            return papers
            
        except Exception as e:
            error_str = str(e)
            # Trigger exponential backoff on 429 rate limit errors
            if "429" in error_str:
                self._handle_rate_limit_error()
            logger.error(f"ArXiv search failed for {query}: {e}")
            console.print(f"[yellow]ArXiv search failed: {e}[/]")
            return []
    
    @log_timing("Search Semantic Scholar")
    def search_semantic_scholar(self, query: str, limit: int = 10) -> list[dict]:
        """Search Semantic Scholar for papers."""
        logger.info(f"Searching Semantic Scholar for: {query}")
        console.print(f"[dim]Searching Semantic Scholar for: {query}[/]")
        
        try:
            # Respect adaptive backoff, or use a 5s base delay for SS
            self._rate_limit(base_sleep=5.0)
            
            url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            # Request affiliations
            params = {
                "query": query,
                "limit": limit,
                "fields": "title,abstract,authors.name,authors.affiliations,year,citationCount,openAccessPdf"
            }
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting gracefully
            if response.status_code == 429:
                console.print("[dim]Rate limited, waiting...[/]")
                self._handle_rate_limit_error()
                return []
            
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for paper in data.get("data", []):
                pdf_url = None
                if paper.get("openAccessPdf"):
                    pdf_url = paper["openAccessPdf"].get("url")
                
                # Process authors and affiliations
                authors = []
                has_rit_affiliation = False
                
                for a in paper.get("authors", []):
                    name = a.get("name", "")
                    authors.append(name)
                    
                    # AFFILIATION CHECK
                    affiliations = a.get("affiliations", [])
                    for aff in affiliations:
                        if isinstance(aff, str):
                            aff_lower = aff.lower()
                            if "rochester" in aff_lower or "rit" in aff_lower:
                                has_rit_affiliation = True
                                break
                
                # Strict Filter: Must have RIT/Rochester affiliation OR allow if explicitly searched?
                # For now, let's mark it but keep it if matches name well.
                # Actually, user wants to avoid "John Smith" ambiguity.
                # So if name is common and NO affiliation match, skip or deprioritize.
                
                # Heuristic: If query matches author name, we trust SS ranking usually,
                # BUT if we see explicit affiliations and NONE match RIT, it's suspicious.
                # Semantic Scholar affiliations are often empty though.
                # Compromise: Keep if strong name match.
                
                papers.append({
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": authors,
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "pdf_url": pdf_url,
                    "source": "semantic_scholar",
                    "has_rit_affiliation": has_rit_affiliation
                })
            
            return papers
            
        except Exception as e:
            logger.error(f"Semantic Scholar search failed for {query}: {e}")
            console.print(f"[yellow]Semantic Scholar search failed: {e}[/]")
            return []
    
    @log_timing("Download PDF")
    def download_pdf(self, url: str, filename: str) -> Optional[Path]:
        """Download a PDF file."""
        if not url:
            return None
        
        if self._is_blacklisted(url):
            logger.debug(f"Skipping blacklisted dead URL: {url}")
            return None
        
        filepath = self.pdf_dir / f"{filename}.pdf"
        
        # Skip if already exists
        if filepath.exists():
            console.print(f"[dim]Already have: {filename}[/]")
            return filepath
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.session.get(url, timeout=60, stream=True)
                
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 10
                    console.print(f"[yellow]Rate limited on PDF. Waiting {wait_time}s...[/]")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get('content-type', '')
                if 'pdf' not in content_type.lower() and not url.endswith('.pdf'):
                    console.print(f"[yellow]Not a PDF: {url}[/]")
                    return None
                
                # Download
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self._inc_downloaded()
                logger.info(f"Successfully downloaded PDF: {filename} from {url}")
                console.print(f"[green]✓ Downloaded: {filename}[/]")
                return filepath
                
            except Exception as e:
                import requests
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 404:
                    logger.warning(f"URL permanently dead (404), blacklisting: {url}")
                    console.print(f"[yellow]Dead URL (404), skipping retries: {url}[/]")
                    self._blacklist_url(url)
                    self._inc_failed()
                    return None
                    
                logger.error(f"Download attempt {attempt+1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    logger.debug(f"Retrying download for {filename}...")
                    console.print(f"[yellow]Download attempt {attempt+1} failed ({e}). Retrying...[/]")
                    time.sleep(2)
                else:
                    self._inc_failed()
                    logger.error(f"Failed to download {filename} after {max_retries} attempts: {e}")
                    console.print(f"[red]Failed to download {filename} after {max_retries} attempts: {e}[/]")
                    return None

        # All retries exhausted (e.g. repeated 429s without raising an exception)
        self._inc_failed()
        logger.error(f"Failed to download {filename} after {max_retries} attempts (rate-limited)")
        return None
    
    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF using VisionCrawler (Marker-PDF).
        Falls back to PyMuPDF if VisionCrawler fails or is not available.
        """
        if not pdf_path.exists():
            return ""

        # Try Vision Extraction first
        try:
            result = self.vision_crawler.convert(
                str(pdf_path),
                pdf_backend=getattr(self.config, 'PDF_BACKEND', 'pymupdf'),
                table_strategy=getattr(self.config, 'TABLE_STRATEGY', 'auto'),
                render_dpi=96
            )
            # Type guard: VisionCrawler can return a bare str on certain failure paths.
            # Calling .get() on a str raises AttributeError: 'str' object has no attribute 'get'.
            if isinstance(result, dict):
                return result.get("content", "")
            elif isinstance(result, str):
                logger.warning(
                    f"Vision extraction returned str instead of dict for {pdf_path.name}. "
                    f"Using raw string. Preview: {result[:80]!r}"
                )
                return result
            else:
                logger.error(
                    f"Vision extraction returned unexpected type {type(result).__name__} "
                    f"for {pdf_path.name}. Falling back to PyMuPDF."
                )
                raise ValueError(f"Unexpected VisionCrawler return type: {type(result)}")
        except Exception as e:
            logger.error(f"Vision extraction failed for {pdf_path.name}: {e}")
            console.print(f"[red]Vision extraction failed for {pdf_path.name}: {e}[/]")
            console.print("[yellow]Falling back to PyMuPDF (Legacy)...[/]")
        
        # Fallback to PyMuPDF
        if not PYMUPDF_AVAILABLE:
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            # Extract first N pages (enough for abstract and intro)
            for page_num in range(min(len(doc), self.config.PDF_MAX_PAGES)):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            doc.close()
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Legacy PyMuPDF text extraction failed for {pdf_path.name}: {e}")
            console.print(f"[yellow]Legacy text extraction failed: {e}[/]")
            return ""
    
    def save_paper_metadata(self, paper: dict, text_content: str = ""):
        """Save paper metadata to JSON."""
        title = paper.get("title", "untitled")
        author = paper.get("authors", ["unknown"])[0] if paper.get("authors") else "unknown"
        
        filename = self._get_safe_filename(title, author)
        metadata_path = self.papers_dir / f"{filename}.json"
        
        paper_data = {
            **paper,
            "extracted_text": text_content[:50000] if text_content else "",  # Limit size
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(paper_data, f, indent=2)
        
        return metadata_path
    
    def search_for_faculty(self, faculty_name: str, interests: Optional[list[str]] = None, limit: int = 10) -> list[dict]:
        """Search for papers by a faculty member."""
        papers = []
        
        # Distribute limit across sources (approximate)
        source_limit = max(5, limit // 2)
        
        # Search by name using proper author format
        arxiv_papers = self.search_arxiv(faculty_name, max_results=source_limit, is_author=True)
        papers.extend(arxiv_papers)
        
        # Search by interests
        if interests:
            # We don't want to blow up the search with too many interest queries
            # So we keep interests limit smaller but proportional
            interest_limit = max(3, limit // 5) 
            for interest in interests[:3]:  # Limit to top 3 interests
                interest_papers = self._cached_search(
                    interest, 
                    source=f"arxiv_interest_{interest_limit}", 
                    search_fn=self.search_arxiv, 
                    max_results=interest_limit
                )
                papers.extend(interest_papers)
        
        # Also try Semantic Scholar
        ss_papers = self.search_semantic_scholar(faculty_name, limit=source_limit)
        papers.extend(ss_papers)
        
        return papers

    
    def _is_author_match(self, faculty_name: str, paper_authors: list[str]) -> bool:
        """
        Check if faculty name matches any author in the paper's author list.
        Handles:
        - Exact match: "John Smith" == "John Smith"
        - First Initial: strictly check if "J. Smith" matches "John Smith" but prevent
          "James Smith" from matching "John Smith".
        """
        if not paper_authors:
            return False
            
        def normalize(name):
            return re.sub(r'[^\w\s]', '', name.lower()).strip()
            
        fac_norm = normalize(faculty_name)
        fac_parts = fac_norm.split()
        if not fac_parts:
            return False
        
        fac_last = fac_parts[-1]
        fac_first = fac_parts[0] if len(fac_parts) > 0 else ""
        fac_first_initial = fac_first[0] if fac_first else ""
        
        for author in paper_authors:
            auth_norm = normalize(author)
            auth_parts = auth_norm.split()
            if not auth_parts:
                continue
            
            auth_last = auth_parts[-1]
            auth_first = auth_parts[0] if len(auth_parts) > 0 else ""
            
            # 1. Last Name Mismatch -> No match
            if fac_last != auth_last:
                continue
                
            # 2. Last Name Match. Now check First Name
            auth_first_initial = auth_first[0] if auth_first else ""
            
            # If both have full first names, they must match exactly (or be highly similar)
            if len(fac_first) > 1 and len(auth_first) > 1:
                 # Check exact first name match or common variations
                 if fac_first == auth_first:
                     return True
                 # If full first names don't match, stringently reject (James != John)
                 continue
                 
            # 3. Handle Initial cases ("J Smith" vs "John Smith")
            if fac_first_initial == auth_first_initial:
                 # Note: This is still slightly prone to "J. Smith" matching "John" and "James"
                 # But it prevents "James" matching "John". For a "J. Smith" search matching "John Smith" paper,
                 # we accept it as a weak match but keep it.
                 return True
                 
        return False

    def _process_faculty_member(self, prof: dict, max_per_faculty: int, progress: Progress, task_id: TaskID) -> tuple[list, int]:
        """Process a single faculty member - searching and downloading papers."""
        prof_start = time.time()
        name = prof.get("name", "")
        downloaded = []
        candidates_found = 0
        
        if not name or len(name) < 3:
            progress.advance(task_id)
            return [], 0
            
        # Get interests (SmartCrawler uses 'research_interests')
        interests = prof.get("research_interests", [])
        
        # Fallback for legacy data
        if not interests:
             interests = prof.get("research_areas", [])
             
        progress.update(task_id, description=f"Searching: {name}")
        
        # Search for papers
        # We fetch MORE than the limit to allow for filtering
        with Timer(f"Searching papers for {name}", use_rich=False) as search_timer:
            papers = self.search_for_faculty(name, interests[:3], limit=max_per_faculty * 2)
        search_duration = search_timer.duration or 0
        
        # STRICT FILTERING LOGIC
        filtered_papers = []
        
        for p in papers:
            # Check if faculty is an author
            if self._is_author_match(name, p.get("authors", [])):
                console.print(f"[bold green]DEBUG: ACCEPTED {p['title'][:30]}... for {name}[/]")
                filtered_papers.append(p)
            else:
                # console.print(f"[dim]REJECTED {p['title'][:40]}... (Author mismatch: {name} not in {p['authors']})[/]")
                pass
        
        # PROACTIVE ASSERTION
        for fp in filtered_papers:
            if not self._is_author_match(name, fp.get("authors", [])):
                 msg = f"CRITICAL LOGIC FAILURE: Accepted {fp['title']} for {name} but it fails match check! Authors: {fp['authors']}"
                 logger.critical(msg)
                 console.print(f"[bold red]{msg}[/]")
                 # Remove it forcefully if logic fails
                 filtered_papers.remove(fp)

        candidates_found = len(filtered_papers)
        # console.print(f"[cyan]Found {candidates_found} strict matches for {name}[/]")

        # Sort by year (descending) to get latest papers
        try:
             filtered_papers.sort(key=lambda x: int(x.get("year") or 0), reverse=True)
        except:
             pass
             
        papers = filtered_papers
        
        # Download PDFs
        prof_downloaded = 0
        for paper in papers[:max_per_faculty]:
            if paper.get("pdf_url"):
                filename = self._get_safe_filename(
                    paper.get("title", ""),
                    paper.get("authors", [""])[0]
                )
                
                pdf_path = self.download_pdf(paper["pdf_url"], filename)
                
                if pdf_path:
                    # Extract text
                    with Timer(f"Extracting text for {filename}", use_rich=False) as extract_timer:
                        text = self.extract_text(pdf_path)
                    extract_duration = extract_timer.duration or 0
                    
                    # Save metadata
                    paper["faculty"] = name
                    paper["pdf_local"] = str(pdf_path)
                    self.save_paper_metadata(paper, text)
                    
                    downloaded.append(paper)
                    prof_downloaded += 1
        
        prof_duration = time.time() - prof_start
        console.print(f"[green]   ✓ Processed {name}: {prof_downloaded} papers ({prof_duration:.2f}s)[/]")
        progress.advance(task_id)
        
        return downloaded, candidates_found
        
    def download_faculty_papers(self, rit_data: dict, max_per_faculty: int = 3):
        """Download papers for all faculty members using multithreading."""
        total_start_time = time.time()
        downloaded_papers = [] # Track papers downloaded in this run
        total_papers = []      # Track all successful papers (same as downloaded_papers basically)
        total_candidates = 0   # Track total papers found in search
        
        # Check if we have the new list format or the dictionary format
        if isinstance(rit_data, list):
             faculty = rit_data
        else:
             faculty = rit_data.get("faculty", [])
        
        # Use concurrency from config, but limit for Vision Crawler
        # Vision models are heavy, so we default to 1 or 2 workers max if not specified
        # to prevent OOM on standard machines.
        max_workers = getattr(self.config, 'CONCURRENCY', 2)
        
        console.print(Panel(f"🚀 Starting Paper Download\n[dim]Faculty Count: {len(faculty)}\nMax Papers/Prof: {max_per_faculty}\nConcurrency: {max_workers} threads[/]", style="bold blue"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} faculty"),
            console=console
        ) as progress:
            task = progress.add_task("Processing faculty...", total=len(faculty))
            
            # Use ThreadPoolExecutor for concurrent processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_prof = {
                    executor.submit(self._process_faculty_member, prof, max_per_faculty, progress, task): prof 
                    for prof in faculty
                }
                
                # Process as they complete
                for future in as_completed(future_to_prof):
                    prof = future_to_prof[future]
                    try:
                        p_downloaded, p_candidates = future.result()
                        total_papers.extend(p_downloaded)
                        downloaded_papers.extend(p_downloaded)
                        total_candidates += p_candidates
                    except Exception as exc:
                        name = prof.get("name", "Unknown")
                        logger.error(f"Generated an exception processing {name}: {exc}")
                        console.print(f"[red]Generated an exception for {name}: {exc}[/]")
        
        total_duration = time.time() - total_start_time
        
        # Summary Table
        table = Table(title="📚 Paper Download Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        unique_pdfs = len(list(self.pdf_dir.glob("*.pdf")))
        
        table.add_row("Total Time", str(timedelta(seconds=int(total_duration))))
        table.add_row("Faculty Processed", str(len(faculty)))
        table.add_row("Candidates Found", str(total_candidates))
        table.add_row("Papers Downloaded (this run)", str(len(total_papers)))
        table.add_row("Total Unique PDFs on Disk", str(unique_pdfs))
        table.add_row("Failed Downloads", str(self.failed_count))
        table.add_row("Concurrency", str(max_workers))
        
        console.print(table)
        return total_papers


def download_all_papers(config: CrawlConfig = RESTRICTED_CONFIG):
    """Main function to download research papers."""
    # Generate a unique trace ID for this entire crawler run
    trace_id = generate_trace_id()
    logger.info(f"Starting new paper crawler run. Trace ID: {trace_id}")
    
    # Load RIT data
    data_file = config.OUTPUT_FILE
    
    if not data_file.exists():
        console.print(f"[red]No RIT data found at {data_file}. Run crawler first.[/]")
        return []
    
    with open(data_file) as f:
        rit_data = json.load(f)
    
    # Download papers
    downloader = PaperDownloader(config)
    papers = downloader.download_faculty_papers(rit_data, config.PAPER_LIMIT_PER_FACULTY)
    
    # Save summary
    summary_file = config.PUBLICATIONS_DIR / "download_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "total_papers": len(papers),
            "downloaded": downloader.downloaded_count,
            "failed": downloader.failed_count,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2)
    
    return papers


def index_downloaded_papers(config: CrawlConfig = RESTRICTED_CONFIG):
    """Index downloaded papers into the vector store."""
    from ..database import get_vector_store
    from ..utils.tag_generator import extract_tags_from_text
    
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    except ImportError:
        console.print("[red]Missing required dependency. Run: pip install langchain-text-splitters[/]")
        return 0
    
    console.print("[bold blue]📦 Indexing downloaded papers...[/]")
    
    # Get vector store (it needs an update to accept config too, or we manage it globally)
    # For now, let's assume get_vector_store needs an update or we construct it here.
    # The VectorStore class needs to know the collection name and directory.
    # We will update VectorStore to accept config.
    store = get_vector_store(config) # We will update this signature
    store.initialize()
    
    documents = []
    seen_ids = set()
    
    # Read all paper metadata files
    for paper_file in config.PAPERS_DIR.glob("*.json"):
        try:
            with open(paper_file) as f:
                paper = json.load(f)
            
            title = paper.get("title", "")
            if not title:
                continue
            
            # Create unique ID
            doc_id = f"paper_{hashlib.md5(title.encode()).hexdigest()[:12]}"
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            
            # Extract tags from title + abstract
            text = f"{title} {paper.get('abstract', '')}"
            tags = extract_tags_from_text(text)
            tag_names = [t[0] for t in tags[:15]]
            
            # Split extracted text into chunks
            extracted_full = paper.get("extracted_text", "")
            abstract = paper.get("abstract", "")
            if not extracted_full:
                 chunks = [abstract] if abstract else []
            else:
                 chunks = text_splitter.split_text(extracted_full)
                 
            authors = ", ".join(paper.get("authors", [])[:5])
            
            # Map each chunk to a unique document in the vector store
            for i, chunk_text in enumerate(chunks):
                 chunk_id = f"{doc_id}_chunk{i}"
                 
                 content = f"""Research Paper: {title}
Authors: {authors}
Year: {paper.get('year', 'Unknown')}
Citations: {paper.get('citations', 'Unknown')}
Faculty: {paper.get('faculty', '')}
Tags: {', '.join(tag_names) if tag_names else 'research'}

Excerpt: {chunk_text}"""
                
                 documents.append({
                     "id": chunk_id,
                     "content": content,
                     "metadata": {
                         "doc_type": "paper",
                         "title": title[:200],
                         "authors": authors,
                         "year": str(paper.get("year", "")),
                         "citations": str(paper.get("citations", 0)),
                         "tags": json.dumps(tag_names),
                         "has_pdf": "yes" if paper.get("pdf_local") else "no",
                         "chunk_index": str(i)
                     }
                 })
            
        except Exception as e:
            console.print(f"[yellow]Error reading {paper_file}: {e}[/]")
    
    if documents:
        store.add_documents(documents)
        console.print(f"[green]✓ Indexed {len(documents)} paper chunks[/]")
    
    return len(documents)
