"""Web crawler for RIT Computing research pages."""

import json
import time
import re
from typing import Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config import RIT_RESEARCH_URL, CRAWL_DELAY, DATA_DIR

console = Console()


class RITCrawler:
    """Crawler for RIT Golisano College research areas and faculty."""

    BASE_URL = "https://www.rit.edu"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TigerResearchBuddy/1.0 (RIT Student Research Tool)"
        })
        self.research_areas = []
        self.faculty = []

    def crawl_research_areas(self) -> list[dict]:
        """Crawl the main research areas page."""
        console.print("[bold blue]🔍 Crawling RIT research areas...[/]")
        
        try:
            response = self.session.get(RIT_RESEARCH_URL)
            response.raise_for_status()
        except requests.RequestException as e:
            console.print(f"[red]Error fetching page: {e}[/]")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        
        # Find all research area links
        research_areas = []
        
        # Look for the research area cards/links
        # These are typically in anchor tags with specific patterns
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # Filter for research area links
            if self._is_research_area_link(href, text):
                area = {
                    "name": text,
                    "url": self._normalize_url(href),
                    "description": "",
                    "faculty": []
                }
                
                # Avoid duplicates
                if area["name"] and area not in research_areas:
                    research_areas.append(area)

        # Dedupe by name
        seen = set()
        unique_areas = []
        for area in research_areas:
            if area["name"] not in seen:
                seen.add(area["name"])
                unique_areas.append(area)

        self.research_areas = unique_areas
        console.print(f"[green]✓ Found {len(unique_areas)} research areas[/]")
        
        return unique_areas

    def _is_research_area_link(self, href: str, text: str) -> bool:
        """Determine if a link is a research area."""
        research_keywords = [
            "artificial-intelligence", "bioinformatics", "computing-education",
            "data-science", "systems", "game-design", "geo-computing",
            "graphics", "visualization", "health-informatics", "hci",
            "accessibility", "interactive-media", "iot", "mobile",
            "pervasive", "networking", "programming-languages",
            "security", "privacy", "software-engineering", "theory"
        ]
        
        # Check if URL contains research-related keywords
        href_lower = href.lower()
        for keyword in research_keywords:
            if keyword in href_lower:
                return True
        
        # Also check by text content
        text_lower = text.lower()
        research_terms = [
            "intelligence", "informatics", "computing", "science",
            "security", "engineering", "systems", "design", "media"
        ]
        return any(term in text_lower for term in research_terms) and len(text) > 3

    def _normalize_url(self, url: str) -> str:
        """Convert relative URLs to absolute."""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{self.BASE_URL}{url}"
        return f"{self.BASE_URL}/{url}"

    def crawl_area_details(self, area: dict) -> dict:
        """Crawl a specific research area page for more details."""
        time.sleep(CRAWL_DELAY)  # Be respectful
        
        try:
            response = self.session.get(area["url"])
            response.raise_for_status()
        except requests.RequestException:
            return area

        soup = BeautifulSoup(response.text, "lxml")
        
        # Try to get description from meta or first paragraph
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc:
            area["description"] = meta_desc.get("content", "")
        
        # Look for faculty links
        faculty_links = []
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "/directory/" in href or "/people/" in href:
                name = link.get_text(strip=True)
                if name and len(name) > 2:
                    faculty_links.append({
                        "name": name,
                        "url": self._normalize_url(href)
                    })
        
        area["faculty"] = faculty_links
        return area

    def crawl_all(self, include_details: bool = True) -> dict:
        """Run full crawl and return all data."""
        # Get research areas
        areas = self.crawl_research_areas()
        
        if include_details:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(
                    "Fetching area details...", 
                    total=len(areas)
                )
                
                for area in areas:
                    area = self.crawl_area_details(area)
                    progress.advance(task)
        
        # Also find faculty from the computing directory
        faculty = self._crawl_faculty_directory()
        
        data = {
            "research_areas": areas,
            "faculty": faculty,
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return data

    def _crawl_faculty_directory(self) -> list[dict]:
        """Crawl faculty from research area pages (more reliable than directory)."""
        console.print("[bold blue]🔍 Extracting faculty from research areas...[/]")
        
        # Collect unique faculty from research areas
        faculty_map = {}  # name -> data
        
        for area in self.research_areas:
            for fac in area.get("faculty", []):
                # Clean faculty name (remove newlines and extra spaces)
                name = fac.get("name", "")
                name = re.sub(r'\s+', ' ', name).strip()
                
                # Remove title suffixes that got concatenated
                name_parts = re.split(r'(?:Professor|Director|Associate|Assistant)', name, maxsplit=1)
                if name_parts:
                    name = name_parts[0].strip()
                
                if not name or len(name) < 3:
                    continue
                
                url = fac.get("url", "")
                
                # Only add if we haven't seen this faculty or this URL is better
                if name not in faculty_map:
                    faculty_map[name] = {
                        "name": name,
                        "title": "",
                        "profile_url": self._normalize_url(url) if url else "",
                        "department": "",
                        "bio": "",
                        "research_interests": [],
                        "research_areas": [area.get("name", "")]
                    }
                else:
                    # Add this research area to existing faculty
                    if area.get("name") not in faculty_map[name].get("research_areas", []):
                        faculty_map[name].setdefault("research_areas", []).append(area.get("name", ""))
        
        faculty = list(faculty_map.values())
        console.print(f"[green]✓ Found {len(faculty)} unique faculty members[/]")
        return faculty

    def crawl_faculty_profile(self, profile_url: str) -> dict:
        """Crawl individual faculty profile page for detailed info."""
        if not profile_url:
            return {}
            
        time.sleep(CRAWL_DELAY)
        
        try:
            response = self.session.get(profile_url)
            response.raise_for_status()
        except requests.RequestException:
            return {}
        
        soup = BeautifulSoup(response.text, "lxml")
        profile_data = {}
        
        # Extract title
        title_elem = soup.find(class_=re.compile(r"title|position|role", re.I))
        if title_elem:
            profile_data["title"] = title_elem.get_text(strip=True)
        
        # Extract department
        dept_elem = soup.find(class_=re.compile(r"department|school|college", re.I))
        if dept_elem:
            profile_data["department"] = dept_elem.get_text(strip=True)
        
        # Extract bio/about
        bio_elem = soup.find(class_=re.compile(r"bio|about|description|summary", re.I))
        if bio_elem:
            profile_data["bio"] = bio_elem.get_text(strip=True)[:2000]  # Limit length
        
        # Extract research interests
        interests = []
        interests_section = soup.find(class_=re.compile(r"interest|research|expertise|specialty", re.I))
        if interests_section:
            for item in interests_section.find_all(["li", "span", "a"]):
                interest = item.get_text(strip=True)
                if interest and len(interest) < 100:
                    interests.append(interest)
        
        if interests:
            profile_data["research_interests"] = interests[:20]  # Limit to 20
        
        # Extract email
        email_link = soup.find("a", href=re.compile(r"mailto:"))
        if email_link:
            email = email_link.get("href", "").replace("mailto:", "").strip()
            profile_data["email"] = email
        
        return profile_data

    def crawl_all_profiles(self, faculty: list[dict], max_profiles: int = 200) -> list[dict]:
        """Crawl individual profile pages for all faculty."""
        console.print(f"[bold blue]🔍 Crawling {min(len(faculty), max_profiles)} faculty profiles...[/]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                "Fetching profiles...",
                total=min(len(faculty), max_profiles)
            )
            
            for i, fac in enumerate(faculty[:max_profiles]):
                if fac.get("profile_url"):
                    profile_data = self.crawl_faculty_profile(fac["profile_url"])
                    
                    # Merge profile data
                    for key, value in profile_data.items():
                        if value:
                            fac[key] = value
                
                progress.advance(task)
        
        console.print(f"[green]✓ Crawled {min(len(faculty), max_profiles)} faculty profiles[/]")
        return faculty

    def crawl_all(self, include_details: bool = True, crawl_profiles: bool = True) -> dict:
        """Run full crawl and return all data."""
        # Get research areas
        areas = self.crawl_research_areas()
        
        if include_details:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(
                    "Fetching area details...", 
                    total=len(areas)
                )
                
                for area in areas:
                    area = self.crawl_area_details(area)
                    progress.advance(task)
        
        # Extract faculty from research areas (more reliable)
        faculty = self._crawl_faculty_directory()
        
        # Optionally crawl individual profiles
        if crawl_profiles and faculty:
            faculty = self.crawl_all_profiles(faculty)
        
        data = {
            "research_areas": areas,
            "faculty": faculty,
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return data

    def save_data(self, data: dict, filename: str = "rit_data.json") -> Path:
        """Save crawled data to JSON file."""
        filepath = DATA_DIR / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓ Saved data to {filepath}[/]")
        return filepath


def crawl_rit(crawl_profiles: bool = True) -> dict:
    """Convenience function to run the crawler."""
    crawler = RITCrawler()
    data = crawler.crawl_all(crawl_profiles=crawl_profiles)
    crawler.save_data(data)
    return data

