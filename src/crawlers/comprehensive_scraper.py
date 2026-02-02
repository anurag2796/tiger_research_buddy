"""Comprehensive faculty and paper scraper with contact details and auto-tagging.

This module provides:
1. Faculty profile scraping with full contact info (email, phone, office)
2. Google Scholar paper scraping  
3. ArXiv paper downloading with proper author parsing
4. AI-powered tag generation from paper content
5. Enhanced semantic search support
"""

import json
import time
import re
import hashlib
from typing import Optional
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..utils.config import DATA_DIR, CRAWL_DELAY

console = Console()


class ComprehensiveScraper:
    """Enhanced scraper for faculty profiles, papers, and contact details."""
    
    BASE_URL = "https://www.rit.edu"
    ARXIV_API = "https://export.arxiv.org/api/query"
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
    
    # Known RIT research areas for auto-tagging
    RESEARCH_KEYWORDS = {
        "machine learning": ["ml", "neural network", "deep learning", "classification", "regression"],
        "artificial intelligence": ["ai", "intelligent", "cognitive", "reasoning", "agent"],
        "natural language processing": ["nlp", "text", "language model", "sentiment", "translation"],
        "computer vision": ["image", "visual", "object detection", "segmentation", "recognition"],
        "cybersecurity": ["security", "encryption", "malware", "vulnerability", "privacy"],
        "data science": ["data mining", "analytics", "big data", "statistics", "visualization"],
        "software engineering": ["software", "testing", "debugging", "code", "development"],
        "human-computer interaction": ["hci", "usability", "accessibility", "user experience", "ux"],
        "bioinformatics": ["genomics", "protein", "biological", "dna", "medical"],
        "distributed systems": ["distributed", "parallel", "cloud", "microservices", "scalability"],
        "game development": ["game", "gaming", "interactive", "vr", "virtual reality"],
        "health informatics": ["health", "medical", "clinical", "patient", "healthcare"],
        "robotics": ["robot", "autonomous", "control", "sensor", "navigation"],
        "networking": ["network", "protocol", "wireless", "communication", "routing"],
        "database systems": ["database", "sql", "query", "storage", "indexing"],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.scraped_faculty = {}
        self.papers = []
        self.rate_limit_delay = 1.5  # seconds between requests

    # ... (other methods) ...

    def download_paper(self, pdf_url: str, filename: str) -> bool:
        """Download a paper PDF."""
        try:
            if not pdf_url:
                return False
                
            # Skip known paywalled domains that falsely report as open access or require specialized scraping
            paywalled_domains = [
                "dl.acm.org", 
                "ieeexplore.ieee.org", 
                "onlinelibrary.wiley.com",
                "springer.com",
                "link.springer.com",
                "sciencedirect.com"
            ]
            if any(domain in pdf_url for domain in paywalled_domains):
                console.print(f"[dim]Skipping likely paywalled source: {pdf_url}[/]")
                return False
            
            # Fix ArXiv URLs: ensure they end with .pdf
            if "arxiv.org/pdf/" in pdf_url and not pdf_url.endswith(".pdf"):
                # Remove version number if present at end (e.g. v1) to get latest, or just append .pdf
                pdf_url = f"{pdf_url}.pdf"
            
            pdf_dir = DATA_DIR / "pdfs"
            pdf_dir.mkdir(exist_ok=True)
            
            filepath = pdf_dir / filename
            if filepath.exists():
                return True
            
            time.sleep(self.rate_limit_delay)
            response = self.session.get(pdf_url, timeout=30, stream=True)
            
            # Handle specific status codes gracefully
            if response.status_code == 403:
                console.print(f"[yellow]Access denied (403) for {pdf_url}[/]")
                return False
            if response.status_code == 404:
                console.print(f"[yellow]PDF not found (404) for {pdf_url}[/]")
                return False
                
            response.raise_for_status()
            
            # Check content type is actually PDF
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type and "application/octet-stream" not in content_type:
                console.print(f"[yellow]Skipping non-PDF content ({content_type}) from {pdf_url}[/]")
                return False
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Failed to download {filename}: {str(e)[:100]}[/]")
            return False
    
    def clean_faculty_name(self, raw_name: str) -> dict:
        """Parse raw faculty name into clean name and title."""
        # Remove newlines and extra whitespace
        name = re.sub(r'\s+', ' ', raw_name).strip()
        
        # Common title patterns
        title_patterns = [
            r'(Assistant Professor|Associate Professor|Professor|Senior Lecturer|Lecturer)',
            r'(Director|Chair|Dean|Head)',
            r'(Academic Advisor|Staff Specialist|Coordinator)',
        ]
        
        extracted_title = ""
        clean_name = name
        
        for pattern in title_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                extracted_title = match.group(1)
                # Remove title and everything after from name
                clean_name = name[:match.start()].strip()
                break
        
        # If title runs into name, try to split
        if not extracted_title:
            # Pattern: "FirstName LastNameTitle"
            for title in ["Assistant Professor", "Associate Professor", "Professor", 
                         "Senior Lecturer", "Lecturer", "Director", "Academic Advisor"]:
                if title.lower().replace(" ", "") in name.lower().replace(" ", ""):
                    idx = name.lower().find(title.lower()[0:5])
                    if idx > 0:
                        clean_name = name[:idx].strip()
                        extracted_title = title
                        break
        
        return {
            "name": clean_name,
            "title": extracted_title,
            "raw_name": raw_name
        }
    
    def scrape_faculty_profile(self, profile_url: str) -> dict:
        """Scrape detailed faculty profile including contact info."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(profile_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            profile = {
                "url": profile_url,
                "email": None,
                "phone": None,
                "office": None,
                "department": None,
                "bio": None,
                "research_interests": [],
                "education": [],
                "google_scholar_url": None,
                "publications_url": None,
            }
            
            # Extract email
            email_link = soup.find('a', href=re.compile(r'mailto:'))
            if email_link:
                profile["email"] = email_link['href'].replace('mailto:', '').split('?')[0]
            
            # Extract phone
            phone_link = soup.find('a', href=re.compile(r'tel:'))
            if phone_link:
                profile["phone"] = phone_link['href'].replace('tel:', '')
            
            # Look for phone in text
            if not profile["phone"]:
                phone_pattern = re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
                phone_match = phone_pattern.search(response.text)
                if phone_match:
                    profile["phone"] = phone_match.group()
            
            # Extract office location
            office_patterns = [
                r'Office[:\s]+([A-Z0-9]+-\d+[A-Z]?)',
                r'Room[:\s]+([A-Z0-9]+-\d+[A-Z]?)',
                r'Location[:\s]+([A-Z0-9]+-\d+[A-Z]?)',
                r'GOL[- ]?\d+',
                r'Building \d+',
            ]
            for pattern in office_patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    profile["office"] = match.group(0) if match.lastindex is None else match.group(1)
                    break
            
            # Extract department
            dept_elem = soup.find(text=re.compile(r'School of|Department of'))
            if dept_elem:
                profile["department"] = dept_elem.strip()
            
            # Extract bio/about
            bio_sections = soup.find_all(['p', 'div'], class_=re.compile(r'bio|about|description', re.I))
            if bio_sections:
                profile["bio"] = ' '.join([s.get_text(strip=True) for s in bio_sections[:2]])[:1000]
            
            # Extract research interests from various formats
            interest_section = soup.find(text=re.compile(r'Research Interest|Research Area|Specialization', re.I))
            if interest_section:
                parent = interest_section.find_parent(['div', 'section', 'article'])
                if parent:
                    interests = parent.find_all('li')
                    if interests:
                        profile["research_interests"] = [i.get_text(strip=True) for i in interests[:10]]
            
            # Look for Google Scholar link
            scholar_link = soup.find('a', href=re.compile(r'scholar\.google'))
            if scholar_link:
                profile["google_scholar_url"] = scholar_link['href']
            
            # Look for publications/CV link  
            pub_link = soup.find('a', href=re.compile(r'publication|cv|resume', re.I))
            if pub_link:
                profile["publications_url"] = urljoin(self.BASE_URL, pub_link['href'])
            
            return profile
            
        except Exception as e:
            console.print(f"[yellow]Failed to scrape profile {profile_url}: {e}[/]")
            return None
    
    def scrape_all_faculty(self, faculty_list: list, max_faculty: int = 200) -> list:
        """Scrape all faculty profiles with progress bar."""
        enhanced_faculty = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            task = progress.add_task("Scraping faculty profiles...", total=min(len(faculty_list), max_faculty))
            
            for faculty in faculty_list[:max_faculty]:
                # Clean the name
                name_info = self.clean_faculty_name(faculty.get("name", ""))
                
                # Scrape profile
                profile_url = faculty.get("url", "")
                if profile_url:
                    # Normalize URL
                    if not profile_url.startswith('http'):
                        profile_url = urljoin(self.BASE_URL, profile_url)
                    
                    profile_data = self.scrape_faculty_profile(profile_url)
                    
                    enhanced_faculty.append({
                        "name": name_info["name"],
                        "title": name_info["title"],
                        "url": profile_url,
                        **({k: v for k, v in (profile_data or {}).items() if k != "url"})
                    })
                
                progress.update(task, advance=1)
        
        return enhanced_faculty
    
    def search_google_scholar(self, author_name: str, max_papers: int = 10) -> list:
        """Search Google Scholar for papers by author (using Semantic Scholar API as it's more reliable)."""
        papers = []
        
        try:
            # Use Semantic Scholar's author search
            search_url = f"{self.SEMANTIC_SCHOLAR_API}/author/search"
            params = {"query": author_name, "limit": 3}
            
            time.sleep(self.rate_limit_delay)
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                authors = data.get("data", [])
                
                for author in authors[:1]:  # Take first matching author
                    author_id = author.get("authorId")
                    if author_id:
                        # Get author's papers
                        papers_url = f"{self.SEMANTIC_SCHOLAR_API}/author/{author_id}/papers"
                        papers_params = {
                            "fields": "title,abstract,year,citationCount,openAccessPdf,url,authors",
                            "limit": max_papers
                        }
                        
                        time.sleep(self.rate_limit_delay)
                        papers_response = self.session.get(papers_url, params=papers_params, timeout=15)
                        
                        if papers_response.status_code == 200:
                            papers_data = papers_response.json()
                            papers = papers_data.get("data", [])
                            
        except Exception as e:
            console.print(f"[yellow]Scholar search failed for {author_name}: {e}[/]")
        
        return papers
    
    def search_arxiv(self, query: str, max_results: int = 10) -> list:
        """Search ArXiv for papers."""
        papers = []
        
        try:
            # Clean and format query properly
            clean_query = re.sub(r'[^\w\s]', '', query)
            
            params = {
                "search_query": f"all:{clean_query}",
                "max_results": max_results,
                "sortBy": "relevance"
            }
            
            time.sleep(self.rate_limit_delay)
            response = self.session.get(self.ARXIV_API, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                entries = soup.find_all('entry')
                
                for entry in entries:
                    title = entry.find('title')
                    abstract = entry.find('summary')
                    published = entry.find('published')
                    pdf_link = entry.find('link', {'title': 'pdf'})
                    
                    papers.append({
                        "title": title.text.strip() if title else "",
                        "abstract": abstract.text.strip() if abstract else "",
                        "year": published.text[:4] if published else "",
                        "pdf_url": pdf_link['href'] if pdf_link else None,
                        "source": "arxiv"
                    })
                    
        except Exception as e:
            console.print(f"[yellow]ArXiv search failed for {query}: {e}[/]")
        
        return papers
    
    def generate_tags_from_text(self, text: str) -> list:
        """Generate research tags from text using keyword matching."""
        if not text:
            return []
        
        text_lower = text.lower()
        tags = set()
        
        for category, keywords in self.RESEARCH_KEYWORDS.items():
            # Check if category name is in text
            if category.lower() in text_lower:
                tags.add(category)
                continue
            
            # Check for keywords
            for keyword in keywords:
                if keyword in text_lower:
                    tags.add(category)
                    break
        
        # Also extract n-grams as potential tags
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)
        
        # Common research terms to tag
        tech_keywords = [
            "transformer", "bert", "gpt", "lstm", "cnn", "rnn", "gan",
            "kubernetes", "docker", "serverless", "microservice",
            "blockchain", "iot", "edge computing", "federated learning",
            "reinforcement learning", "transfer learning", "few-shot",
            "llm", "large language model", "prompt", "fine-tuning"
        ]
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                tags.add(keyword.replace(" ", "_"))
        
        return list(tags)
    
    
    def scrape_comprehensive(self, faculty_list: list, max_papers_per_faculty: int = 10) -> dict:
        """Run comprehensive scraping: faculty profiles, papers, and tags."""
        console.print("[bold blue]Starting comprehensive data collection...[/]")
        
        # 1. Scrape faculty profiles with contact info
        console.print("\n[yellow]Phase 1: Scraping faculty profiles...[/]")
        enhanced_faculty = self.scrape_all_faculty(faculty_list)
        
        # 2. For each faculty, search for papers
        console.print("\n[yellow]Phase 2: Collecting research papers...[/]")
        all_papers = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            task = progress.add_task("Searching papers...", total=len(enhanced_faculty))
            
            for faculty in enhanced_faculty:
                name = faculty.get("name", "")
                if not name or len(name) < 3:
                    progress.update(task, advance=1)
                    continue
                
                # Search Semantic Scholar
                papers = self.search_google_scholar(name, max_papers_per_faculty)
                
                for paper in papers:
                    paper_data = {
                        "title": paper.get("title", ""),
                        "abstract": paper.get("abstract", ""),
                        "year": paper.get("year"),
                        "citations": paper.get("citationCount", 0),
                        "faculty_author": name,
                        "source": "semantic_scholar",
                        "pdf_url": paper.get("openAccessPdf", {}).get("url") if paper.get("openAccessPdf") else None,
                    }
                    
                    # Generate tags from title and abstract
                    text = f"{paper_data['title']} {paper_data['abstract']}"
                    paper_data["auto_tags"] = self.generate_tags_from_text(text)
                    
                    all_papers.append(paper_data)
                
                # Also search ArXiv with first name + last name only
                name_parts = name.split()
                if len(name_parts) >= 2:
                    arxiv_query = f"{name_parts[0]} {name_parts[-1]}"
                    arxiv_papers = self.search_arxiv(arxiv_query, 5)
                    
                    for paper in arxiv_papers:
                        paper["faculty_author"] = name
                        paper["auto_tags"] = self.generate_tags_from_text(
                            f"{paper.get('title', '')} {paper.get('abstract', '')}"
                        )
                        all_papers.append(paper)
                
                progress.update(task, advance=1)
        
        # 3. Download papers with PDF URLs
        console.print("\n[yellow]Phase 3: Downloading papers...[/]")
        downloaded_count = 0
        
        papers_with_pdfs = [p for p in all_papers if p.get("pdf_url")]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            task = progress.add_task("Downloading PDFs...", total=len(papers_with_pdfs))
            
            for paper in papers_with_pdfs:
                # Generate filename
                title_slug = re.sub(r'[^\w\s-]', '', paper.get('title', '')[:50]).strip().replace(' ', '_')
                author_slug = paper.get('faculty_author', 'unknown')[:20].replace(' ', '_')
                filename = f"{author_slug}_{title_slug}.pdf".lower()
                
                if self.download_paper(paper["pdf_url"], filename):
                    paper["local_pdf"] = f"data/pdfs/{filename}"
                    downloaded_count += 1
                
                progress.update(task, advance=1)
        
        # 4. Generate aggregate faculty tags
        console.print("\n[yellow]Phase 4: Generating tags...[/]")
        for faculty in enhanced_faculty:
            name = faculty.get("name", "")
            
            # Collect tags from all papers by this faculty
            faculty_papers = [p for p in all_papers if p.get("faculty_author") == name]
            all_tags = set()
            
            for paper in faculty_papers:
                all_tags.update(paper.get("auto_tags", []))
            
            # Also tag from research interests 
            for interest in faculty.get("research_interests", []):
                all_tags.update(self.generate_tags_from_text(interest))
            
            faculty["auto_tags"] = list(all_tags)
            faculty["paper_count"] = len(faculty_papers)
        
        return {
            "faculty": enhanced_faculty,
            "papers": all_papers,
            "stats": {
                "faculty_count": len(enhanced_faculty),
                "papers_found": len(all_papers),
                "papers_downloaded": downloaded_count,
                "unique_tags": len(set(t for p in all_papers for t in p.get("auto_tags", [])))
            }
        }
    
    def save_results(self, data: dict, filename: str = "comprehensive_data.json"):
        """Save scraped data to JSON."""
        filepath = DATA_DIR / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Saved data to {filepath}[/]")
        return filepath


def run_comprehensive_scrape(max_papers_per_faculty: int = 10) -> dict:
    """Run comprehensive scraping of all faculty and papers."""
    # Load existing RIT data
    rit_data_path = DATA_DIR / "rit_data.json"
    
    if not rit_data_path.exists():
        console.print("[red]No rit_data.json found. Run 'python main.py crawl' first.[/]")
        return None
    
    with open(rit_data_path) as f:
        rit_data = json.load(f)
    
    # Collect all unique faculty
    faculty_seen = set()
    faculty_list = []
    
    for area in rit_data.get("research_areas", []):
        for faculty in area.get("faculty", []):
            url = faculty.get("url", "")
            if url and url not in faculty_seen:
                faculty_seen.add(url)
                faculty_list.append(faculty)
    
    console.print(f"[bold]Found {len(faculty_list)} unique faculty members[/]")
    
    # Run scraper
    scraper = ComprehensiveScraper()
    data = scraper.scrape_comprehensive(faculty_list, max_papers_per_faculty)
    
    # Save results
    scraper.save_results(data)
    
    # Print summary
    console.print("\n[bold green]✓ Comprehensive scrape complete![/]")
    console.print(f"  Faculty with contact info: {data['stats']['faculty_count']}")
    console.print(f"  Papers discovered: {data['stats']['papers_found']}")
    console.print(f"  Papers downloaded: {data['stats']['papers_downloaded']}")
    console.print(f"  Unique research tags: {data['stats']['unique_tags']}")
    
    return data
