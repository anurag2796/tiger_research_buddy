"""Extended RIT crawler for additional research content.

Crawls research centers, labs, news, and other RIT sources.
"""

import re
import time
import json
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config import DATA_DIR

console = Console()

CRAWL_DELAY = 1.5


class ExtendedRITCrawler:
    """Crawl additional RIT sources for research content."""
    
    # Additional RIT URLs to crawl
    SOURCES = {
        "research_centers": [
            "https://www.rit.edu/computing/research",
            "https://www.rit.edu/cybersecurity/research",
        ],
        "phd_research": [
            "https://www.rit.edu/computing/phd-computing-and-information-sciences/research",
        ],
        "news": [
            "https://www.rit.edu/news/search?keyword=computing+research",
            "https://www.rit.edu/news/search?keyword=cybersecurity",
        ],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TigerResearchBuddy/1.0"
        })
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        try:
            time.sleep(CRAWL_DELAY)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except Exception as e:
            console.print(f"[yellow]Could not fetch {url}: {e}[/]")
            return None
    
    def crawl_research_centers(self) -> list[dict]:
        """Crawl research center pages for lab information."""
        console.print("[bold blue]🔬 Crawling research centers...[/]")
        
        centers = []
        
        for url in self.SOURCES["research_centers"]:
            soup = self._fetch_page(url)
            if not soup:
                continue
            
            # Find research center/lab sections
            for section in soup.find_all(["section", "div", "article"], class_=re.compile(r"research|center|lab", re.I)):
                title_elem = section.find(["h2", "h3", "h4"])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Get description
                desc_elem = section.find("p")
                description = desc_elem.get_text(strip=True)[:500] if desc_elem else ""
                
                # Get link
                link = section.find("a", href=True)
                center_url = link["href"] if link else ""
                
                if title and len(title) > 5:
                    centers.append({
                        "name": title,
                        "description": description,
                        "url": center_url,
                        "type": "research_center"
                    })
        
        console.print(f"[green]✓ Found {len(centers)} research centers/labs[/]")
        return centers
    
    def crawl_news(self) -> list[dict]:
        """Crawl RIT news for research stories."""
        console.print("[bold blue]📰 Crawling research news...[/]")
        
        articles = []
        
        for url in self.SOURCES["news"]:
            soup = self._fetch_page(url)
            if not soup:
                continue
            
            # Find news articles
            for article in soup.find_all(["article", "div"], class_=re.compile(r"news|article|story|result", re.I)):
                title_elem = article.find(["h2", "h3", "h4", "a"])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Get summary
                summary_elem = article.find("p")
                summary = summary_elem.get_text(strip=True)[:300] if summary_elem else ""
                
                # Get link
                link = article.find("a", href=True)
                article_url = link["href"] if link else ""
                
                # Get date
                date_elem = article.find(class_=re.compile(r"date|time", re.I))
                date = date_elem.get_text(strip=True) if date_elem else ""
                
                if title and len(title) > 10:
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "url": article_url,
                        "date": date,
                        "type": "news"
                    })
        
        console.print(f"[green]✓ Found {len(articles)} news articles[/]")
        return articles[:50]  # Limit to 50 most recent
    
    def crawl_phd_research(self) -> list[dict]:
        """Crawl PhD research topics and dissertations."""
        console.print("[bold blue]🎓 Crawling PhD research areas...[/]")
        
        topics = []
        
        for url in self.SOURCES["phd_research"]:
            soup = self._fetch_page(url)
            if not soup:
                continue
            
            # Find research topic sections
            for section in soup.find_all(["section", "div", "article"]):
                title_elem = section.find(["h2", "h3", "h4"])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Skip generic titles
                if title.lower() in ["research", "research areas", "overview"]:
                    continue
                
                desc_elem = section.find("p")
                description = desc_elem.get_text(strip=True)[:500] if desc_elem else ""
                
                # Find faculty associated with this topic
                faculty = []
                for link in section.find_all("a", href=re.compile(r"/directory/")):
                    faculty.append(link.get_text(strip=True))
                
                if title and len(title) > 5:
                    topics.append({
                        "name": title,
                        "description": description,
                        "faculty": faculty[:10],
                        "type": "phd_research"
                    })
        
        console.print(f"[green]✓ Found {len(topics)} PhD research topics[/]")
        return topics
    
    def crawl_all(self) -> dict:
        """Crawl all extended sources."""
        data = {
            "research_centers": self.crawl_research_centers(),
            "news": self.crawl_news(),
            "phd_research": self.crawl_phd_research(),
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return data
    
    def save_data(self, data: dict, filename: str = "extended_data.json") -> Path:
        """Save extended data to JSON."""
        filepath = DATA_DIR / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓ Saved extended data to {filepath}[/]")
        return filepath


def crawl_extended_sources():
    """Convenience function to run the extended crawler."""
    crawler = ExtendedRITCrawler()
    data = crawler.crawl_all()
    crawler.save_data(data)
    return data


def add_extended_to_vectorstore(data_file: str = "extended_data.json"):
    """Add extended crawl data to vector store."""
    from ..database import get_vector_store
    from ..utils.tag_generator import extract_tags_from_text
    
    filepath = DATA_DIR / data_file
    
    if not filepath.exists():
        console.print(f"[yellow]Extended data not found. Run extended crawl first.[/]")
        return
    
    with open(filepath) as f:
        data = json.load(f)
    
    store = get_vector_store()
    store.initialize()
    
    documents = []
    seen_ids = set()
    
    def make_unique_id(prefix: str, name: str, idx: int) -> str:
        """Generate unique document ID."""
        # Clean name for ID
        clean = re.sub(r'[^a-z0-9]', '_', name.lower()[:30])
        base_id = f"{prefix}_{clean}"
        doc_id = f"{base_id}_{idx}"
        while doc_id in seen_ids:
            idx += 1000
            doc_id = f"{base_id}_{idx}"
        seen_ids.add(doc_id)
        return doc_id
    
    # Add research centers
    for i, center in enumerate(data.get("research_centers", [])):
        tags = extract_tags_from_text(f"{center['name']} {center.get('description', '')}")
        tag_names = [t[0] for t in tags[:10]]
        
        doc_id = make_unique_id("center", center['name'], i)
        content = f"""Research Center: {center['name']}
Description: {center.get('description', '')}
Tags: {', '.join(tag_names) if tag_names else 'research'}"""
        
        documents.append({
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "research_center",
                "name": center["name"],
                "tags": str(tag_names)
            }
        })
    
    # Add news articles
    for i, article in enumerate(data.get("news", [])):
        tags = extract_tags_from_text(f"{article['title']} {article.get('summary', '')}")
        tag_names = [t[0] for t in tags[:10]]
        
        doc_id = make_unique_id("news", article['title'], i)
        content = f"""Research News: {article['title']}
Summary: {article.get('summary', '')}
Date: {article.get('date', '')}
Tags: {', '.join(tag_names) if tag_names else 'news'}"""
        
        documents.append({
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "news",
                "title": article["title"][:200],
                "tags": str(tag_names)
            }
        })
    
    # Add PhD research topics
    for i, topic in enumerate(data.get("phd_research", [])):
        tags = extract_tags_from_text(f"{topic['name']} {topic.get('description', '')}")
        tag_names = [t[0] for t in tags[:10]]
        
        doc_id = make_unique_id("phd", topic['name'], i)
        content = f"""PhD Research: {topic['name']}
Description: {topic.get('description', '')}
Faculty: {', '.join(topic.get('faculty', []))}
Tags: {', '.join(tag_names) if tag_names else 'phd'}"""
        
        documents.append({
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "phd_research",
                "name": topic["name"],
                "tags": str(tag_names)
            }
        })
    
    if documents:
        store.add_documents(documents)
        console.print(f"[green]✓ Added {len(documents)} extended documents to vector store[/]")

