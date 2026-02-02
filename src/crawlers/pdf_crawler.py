"""PDF crawler for extracting research papers.

Crawls accessible PDFs from Google Scholar and other sources,
extracts text, and indexes them for search.
"""

import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config import DATA_DIR

console = Console()

# PDF storage directory
PDF_DIR = DATA_DIR / "pdfs"
PDF_DIR.mkdir(exist_ok=True)

# Rate limiting
CRAWL_DELAY = 2.0

# Check if PyMuPDF is available
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    console.print("[yellow]Warning: PyMuPDF not installed. Run 'pip install pymupdf'[/]")


class PDFCrawler:
    """Crawl and extract text from research paper PDFs."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TigerResearchBuddy/1.0"
        })
    
    def download_pdf(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """Download a PDF from URL."""
        if not url:
            return None
        
        # Generate filename from URL if not provided
        if not filename:
            parsed = urlparse(url)
            filename = Path(parsed.path).name
            if not filename.endswith('.pdf'):
                filename = f"{hash(url)}.pdf"
        
        filepath = PDF_DIR / filename
        
        # Skip if already downloaded
        if filepath.exists():
            return filepath
        
        try:
            time.sleep(CRAWL_DELAY)
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower() and not url.endswith('.pdf'):
                return None
            
            # Save PDF
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
            
        except Exception as e:
            console.print(f"[yellow]Could not download {url}: {e}[/]")
            return None
    
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text content from a PDF."""
        if not PYMUPDF_AVAILABLE:
            return ""
        
        if not pdf_path.exists():
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page_num in range(min(len(doc), 20)):  # Limit to first 20 pages
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            doc.close()
            return "\n".join(text_parts)
            
        except Exception as e:
            console.print(f"[yellow]Could not extract text from {pdf_path}: {e}[/]")
            return ""
    
    def get_paper_urls_from_scholar_data(self, data: dict) -> list[dict]:
        """Extract paper URLs from crawled scholar data."""
        papers = []
        
        for prof in data.get("faculty", []):
            scholar = prof.get("scholar", {})
            
            for pub in scholar.get("publications", []):
                title = pub.get("title", "")
                url = pub.get("url", "")
                
                # Try to find PDF link
                pdf_url = None
                if url:
                    # Some common PDF sources
                    if "arxiv.org" in url:
                        # Convert arxiv abstract URL to PDF
                        pdf_url = url.replace("/abs/", "/pdf/") + ".pdf"
                    elif url.endswith(".pdf"):
                        pdf_url = url
                
                if title:
                    papers.append({
                        "title": title,
                        "author": prof.get("name", ""),
                        "url": url,
                        "pdf_url": pdf_url,
                        "year": pub.get("year", ""),
                        "citations": pub.get("citations", 0)
                    })
        
        return papers
    
    def crawl_papers(self, data: dict, max_papers: int = 50) -> list[dict]:
        """Crawl and extract papers from scholar data."""
        console.print("[bold blue]📄 Extracting research papers...[/]")
        
        papers = self.get_paper_urls_from_scholar_data(data)
        console.print(f"[dim]Found {len(papers)} paper references[/]")
        
        extracted = []
        pdf_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                "Processing papers...",
                total=min(len(papers), max_papers)
            )
            
            for paper in papers[:max_papers]:
                pdf_url = paper.get("pdf_url")
                
                if pdf_url:
                    # Try to download and extract
                    filepath = self.download_pdf(pdf_url)
                    
                    if filepath:
                        text = self.extract_text(filepath)
                        
                        if text:
                            paper["content"] = text[:10000]  # Limit content size
                            paper["pdf_path"] = str(filepath)
                            pdf_count += 1
                
                extracted.append(paper)
                progress.advance(task)
        
        console.print(f"[green]✓ Processed {len(extracted)} papers ({pdf_count} with PDFs)[/]")
        return extracted


def extract_papers_to_vectorstore(data_file: str = "rit_data.json"):
    """Extract papers from JSON data and add to vector store."""
    import json
    from ..database import get_vector_store
    from ..utils.tag_generator import generate_tags_for_publication
    
    filepath = DATA_DIR / data_file
    
    if not filepath.exists():
        console.print(f"[red]Data file not found: {filepath}[/]")
        return
    
    with open(filepath) as f:
        data = json.load(f)
    
    crawler = PDFCrawler()
    papers = crawler.crawl_papers(data, max_papers=100)
    
    # Add to vector store
    store = get_vector_store()
    store.initialize()
    
    documents = []
    for i, paper in enumerate(papers):
        if not paper.get("title"):
            continue
        
        # Generate tags
        tags = generate_tags_for_publication(paper)
        tag_names = [t[0] for t in tags[:10]]
        
        # Build content
        content_parts = [
            f"Publication: {paper['title']}",
            f"Author: {paper.get('author', 'Unknown')}",
            f"Year: {paper.get('year', 'Unknown')}",
            f"Citations: {paper.get('citations', 0)}",
            f"Tags: {', '.join(tag_names) if tag_names else 'research'}"
        ]
        
        # Add extracted text if available
        if paper.get("content"):
            # Add abstract/intro (first part of content)
            content_parts.append(f"\nExcerpt: {paper['content'][:2000]}...")
        
        doc_id = f"paper_{i}_{paper['title'][:30].replace(' ', '_')}"
        
        documents.append({
            "id": doc_id,
            "content": "\n".join(content_parts),
            "metadata": {
                "doc_type": "paper",
                "title": paper["title"][:200],
                "author": paper.get("author", ""),
                "year": paper.get("year", ""),
                "tags": str(tag_names)
            }
        })
    
    if documents:
        store.add_documents(documents)
        console.print(f"[green]✓ Added {len(documents)} papers to vector store[/]")
