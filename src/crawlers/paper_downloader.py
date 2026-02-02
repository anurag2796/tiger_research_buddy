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
from pathlib import Path
from typing import Optional, Generator
from urllib.parse import urlparse, quote_plus

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..utils.config import DATA_DIR

console = Console()

# Directories
PDF_DIR = DATA_DIR / "pdfs"
PAPERS_DIR = DATA_DIR / "papers"
PUBLICATIONS_DIR = DATA_DIR / "publications"

# Ensure directories exist
for d in [PDF_DIR, PAPERS_DIR, PUBLICATIONS_DIR]:
    d.mkdir(exist_ok=True)

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
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TigerResearchBuddy/1.0 (RIT Research Assistant; mailto:research@rit.edu)"
        })
        self.downloaded_count = 0
        self.failed_count = 0
    
    def _rate_limit(self):
        """Respect rate limits."""
        time.sleep(RATE_LIMIT)
    
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
    
    def search_arxiv(self, query: str, max_results: int = 10, is_author: bool = False) -> list[dict]:
        """Search ArXiv for papers."""
        console.print(f"[dim]Searching ArXiv for: {query}[/]")
        
        try:
            self._rate_limit()
            
            # Format query properly - ArXiv uses specific field prefixes
            if is_author:
                # Extract just last name for better results
                parts = query.replace(",", "").split()
                if parts:
                    lastname = parts[-1] if len(parts) > 1 else parts[0]
                    search_query = f"au:{lastname}"
                else:
                    search_query = query
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
            console.print(f"[yellow]ArXiv search failed: {e}[/]")
            return []
    
    def search_semantic_scholar(self, query: str, limit: int = 10) -> list[dict]:
        """Search Semantic Scholar for papers."""
        console.print(f"[dim]Searching Semantic Scholar for: {query}[/]")
        
        try:
            # Longer delay for Semantic Scholar (stricter rate limits)
            time.sleep(5)
            
            url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": limit,
                "fields": "title,abstract,authors,year,citationCount,openAccessPdf"
            }
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting gracefully
            if response.status_code == 429:
                console.print("[dim]Rate limited, waiting...[/]")
                time.sleep(30)
                return []
            
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for paper in data.get("data", []):
                pdf_url = None
                if paper.get("openAccessPdf"):
                    pdf_url = paper["openAccessPdf"].get("url")
                
                authors = [a.get("name", "") for a in paper.get("authors", [])]
                
                papers.append({
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": authors,
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "pdf_url": pdf_url,
                    "source": "semantic_scholar"
                })
            
            return papers
            
        except Exception as e:
            console.print(f"[yellow]Semantic Scholar search failed: {e}[/]")
            return []
    
    def download_pdf(self, url: str, filename: str) -> Optional[Path]:
        """Download a PDF file."""
        if not url:
            return None
        
        filepath = PDF_DIR / f"{filename}.pdf"
        
        # Skip if already exists
        if filepath.exists():
            console.print(f"[dim]Already have: {filename}[/]")
            return filepath
        
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=60, stream=True)
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
            
            self.downloaded_count += 1
            console.print(f"[green]✓ Downloaded: {filename}[/]")
            return filepath
            
        except Exception as e:
            self.failed_count += 1
            console.print(f"[yellow]Failed: {filename} - {e}[/]")
            return None
    
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text from a PDF."""
        if not PYMUPDF_AVAILABLE or not pdf_path.exists():
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            # Extract first 30 pages (enough for abstract and intro)
            for page_num in range(min(len(doc), 30)):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            doc.close()
            return "\n".join(text_parts)
            
        except Exception as e:
            console.print(f"[yellow]Text extraction failed: {e}[/]")
            return ""
    
    def save_paper_metadata(self, paper: dict, text_content: str = ""):
        """Save paper metadata to JSON."""
        title = paper.get("title", "untitled")
        author = paper.get("authors", ["unknown"])[0] if paper.get("authors") else "unknown"
        
        filename = self._get_safe_filename(title, author)
        metadata_path = PAPERS_DIR / f"{filename}.json"
        
        paper_data = {
            **paper,
            "extracted_text": text_content[:50000] if text_content else "",  # Limit size
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(paper_data, f, indent=2)
        
        return metadata_path
    
    def search_for_faculty(self, faculty_name: str, interests: list[str] = None) -> list[dict]:
        """Search for papers by a faculty member."""
        papers = []
        
        # Search by name using proper author format
        arxiv_papers = self.search_arxiv(faculty_name, max_results=5, is_author=True)
        papers.extend(arxiv_papers)
        
        # Search by interests
        if interests:
            for interest in interests[:2]:  # Limit to avoid too many requests
                interest_papers = self.search_arxiv(interest, max_results=3)
                papers.extend(interest_papers)
        
        # Also try Semantic Scholar
        ss_papers = self.search_semantic_scholar(faculty_name, limit=5)
        papers.extend(ss_papers)
        
        return papers

    
    def download_faculty_papers(self, rit_data: dict, max_per_faculty: int = 3):
        """Download papers for all faculty members."""
        console.print("[bold blue]📚 Downloading faculty research papers...[/]")
        
        faculty = rit_data.get("faculty", [])
        total_papers = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Searching papers...", total=len(faculty))
            
            for prof in faculty:
                name = prof.get("name", "")
                if not name or len(name) < 3:
                    progress.advance(task)
                    continue
                
                # Get interests from scholar data or research areas
                interests = []
                scholar = prof.get("scholar", {})
                if scholar:
                    interests = scholar.get("interests", [])
                interests.extend(prof.get("research_areas", []))
                
                # Search for papers
                papers = self.search_for_faculty(name, interests[:3])
                
                # Download PDFs
                for paper in papers[:max_per_faculty]:
                    if paper.get("pdf_url"):
                        filename = self._get_safe_filename(
                            paper.get("title", ""),
                            paper.get("authors", [""])[0]
                        )
                        pdf_path = self.download_pdf(paper["pdf_url"], filename)
                        
                        if pdf_path:
                            # Extract text
                            text = self.extract_text(pdf_path)
                            
                            # Save metadata
                            paper["faculty"] = name
                            paper["pdf_local"] = str(pdf_path)
                            self.save_paper_metadata(paper, text)
                            
                            total_papers.append(paper)
                
                progress.advance(task)
        
        console.print(f"\n[bold green]✓ Downloaded {self.downloaded_count} papers ({self.failed_count} failed)[/]")
        return total_papers


def download_all_papers(max_per_faculty: int = 3):
    """Main function to download research papers."""
    # Load RIT data
    data_file = DATA_DIR / "rit_data.json"
    
    if not data_file.exists():
        console.print("[red]No RIT data found. Run 'python main.py crawl' first.[/]")
        return []
    
    with open(data_file) as f:
        rit_data = json.load(f)
    
    # Download papers
    downloader = PaperDownloader()
    papers = downloader.download_faculty_papers(rit_data, max_per_faculty)
    
    # Save summary
    summary_file = PUBLICATIONS_DIR / "download_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "total_papers": len(papers),
            "downloaded": downloader.downloaded_count,
            "failed": downloader.failed_count,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2)
    
    return papers


def index_downloaded_papers():
    """Index downloaded papers into the vector store."""
    from ..database import get_vector_store
    from ..utils.tag_generator import extract_tags_from_text
    
    console.print("[bold blue]📦 Indexing downloaded papers...[/]")
    
    store = get_vector_store()
    store.initialize()
    
    documents = []
    seen_ids = set()
    
    # Read all paper metadata files
    for paper_file in PAPERS_DIR.glob("*.json"):
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
            
            # Build content
            authors = ", ".join(paper.get("authors", [])[:5])
            abstract = paper.get("abstract", "")[:1500]
            extracted = paper.get("extracted_text", "")[:3000]
            
            content = f"""Research Paper: {title}
Authors: {authors}
Year: {paper.get('year', 'Unknown')}
Citations: {paper.get('citations', 'Unknown')}
Abstract: {abstract}
Faculty: {paper.get('faculty', '')}
Tags: {', '.join(tag_names) if tag_names else 'research'}

Excerpt: {extracted}"""
            
            documents.append({
                "id": doc_id,
                "content": content,
                "metadata": {
                    "doc_type": "paper",
                    "title": title[:200],
                    "authors": authors,
                    "year": str(paper.get("year", "")),
                    "citations": str(paper.get("citations", 0)),
                    "tags": json.dumps(tag_names),
                    "has_pdf": "yes" if paper.get("pdf_local") else "no"
                }
            })
            
        except Exception as e:
            console.print(f"[yellow]Error reading {paper_file}: {e}[/]")
    
    if documents:
        store.add_documents(documents)
        console.print(f"[green]✓ Indexed {len(documents)} papers[/]")
    
    return len(documents)
