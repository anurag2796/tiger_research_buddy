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

from ..utils.config import COLLEGE_URLS, CRAWL_DELAY, DATA_DIR

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
        """Crawl research areas for all configured colleges."""
        all_areas = []
        
        for college, url in COLLEGE_URLS.items():
            console.print(f"[bold blue]🔍 Crawling {college.title()} research areas...[/]")
            try:
                areas = self._crawl_college_areas(url, college)
                all_areas.extend(areas)
            except Exception as e:
                console.print(f"[red]Error crawling {college}: {e}[/]")
                
        self.research_areas = all_areas
        return all_areas

    def _crawl_college_areas(self, url: str, college: str) -> list[dict]:
        """Crawl a specific college's research page."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            console.print(f"[red]Error fetching page {url}: {e}[/]")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        
        # Find all research area links
        research_areas = []
        
        # Look for the research area cards/links
        # These are typically in anchor tags with specific patterns
        generic_terms = ["learn more", "read more", "discover", "explore", "view all", "see all", "more info"]
        
        # Look for the research area cards/links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # Filter for research area links
            if self._is_research_area_link(href, text):
                # Handle generic text
                if text.lower() in generic_terms:
                    # Extract last part of URL
                    slug = href.rstrip("/").split("/")[-1]
                    name = slug.replace("-", " ").title()
                else:
                    name = text

                area = {
                    "name": name,
                    "url": self._normalize_url(href),
                    "college": college,
                    "description": "",
                    "faculty": []
                }
                
                # Avoid duplicates
                if area["name"] and len(area["name"]) > 3 and area not in research_areas:
                    research_areas.append(area)

        # Dedupe by name
        seen = set()
        unique_areas = []
        for area in research_areas:
            if area["name"] not in seen and area["name"].lower() not in generic_terms:
                seen.add(area["name"])
                unique_areas.append(area)

        self.research_areas = unique_areas
        console.print(f"[green]✓ Found {len(unique_areas)} research areas[/]")
        
        return unique_areas

    def _is_research_area_link(self, href: str, text: str) -> bool:
        """Determine if a link is a research area."""
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Exclusions: Skip standard footer/nav links
        exclusions = [
            "privacy", "accessibility", "alumni", "directory", "contact", 
            "about", "news", "events", "apply", "visit", "giving", 
            "careers", "login", "sitemap", "clubs", "student", "co-op"
        ]
        
        for term in exclusions:
            if term in href_lower or term in text_lower:
                # Special case: "Privacy" might be a research topic (Security & Privacy), 
                # so check if it's the privacy statement URL specifically
                if "privacy-statement" in href_lower or "privacy-policy" in href_lower:
                    return False
                if term in ["privacy", "accessibility"] and "/research/" in href_lower:
                    # Valid research topic (e.g. Accessibility Research)
                    pass
                else:
                    return False

        # Strong signal: URL contains "/research/" or "/laboratories/"
        if "/research/" in href_lower or "/laboratories/" in href_lower or "/labs/" in href_lower:
            # But filter out the index pages themselves
            if href_lower.endswith("/research") or href_lower.endswith("/research-areas"):
                return False
            return True

        research_keywords = [
            "artificial-intelligence", "bioinformatics", "computing",
            "data-science", "systems", "game-design", 
            "graphics", "visualization", "health-informatics", "hci",
            "interactive-media", "iot", "mobile",
            "networking", "programming",
            "security", "software-engineering", "theory",
            "materials", "photonics", "energy", "manufacturing"
        ]
        
        # Check specific keywords for Computing college legacy links
        for keyword in research_keywords:
            if keyword in href_lower:
                return True
        
        return False

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
        
        # Helper to extract faculty from soup
        def extract_faculty(s):
            links = []
            for link in s.find_all("a", href=True):
                href = link.get("href", "")
                # Regular directory links
                if "/directory/" in href or "/people/" in href:
                    name = link.get_text(strip=True)
                    if name and len(name) > 2 and "View Profile" not in name:
                        links.append({
                            "name": name,
                            "url": self._normalize_url(href)
                        })
            return links

        faculty_links = extract_faculty(soup)
        
        # If no faculty found, check for a "People" or "Faculty" or "Directory" sub-page link
        if not faculty_links:
            console.print(f"[dim]No direct faculty found in {area['name']}, looking for directory link...[/]")
            for link in soup.find_all("a", href=True):
                text = link.get_text(strip=True).lower()
                href = link.get("href", "")
                
                if text in ["people", "faculty", "directory", "our team", "researchers"] or \
                   "directory" in href or "people" in href:
                    
                    # Skip anchor links, search, and main directories
                    if not href or href.startswith("#") or "search" in href or href.endswith("/directory"): 
                         continue

                    sub_url = self._normalize_url(href)
                    console.print(f"[dim]Following link to: {sub_url}[/]")
                    try:
                        time.sleep(CRAWL_DELAY)
                        sub_resp = self.session.get(sub_url)
                        sub_resp.raise_for_status()
                        sub_soup = BeautifulSoup(sub_resp.text, "lxml")
                        new_links = extract_faculty(sub_soup)
                        if new_links:
                            faculty_links.extend(new_links)
                            break # Found them
                    except Exception as e:
                        console.print(f"[dim]Failed to follow sub-link: {e}[/]")

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
                        "college": area.get("college", ""),
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
        
        # Extract title (robust search for h1/h2/div with title classes)
        # Try specific Profile structure first
        title_elem = soup.find("div", class_="field--name-field-profile-title")
        if not title_elem:
            title_elem = soup.find(class_=re.compile(r"profile-title|person-title", re.I))
        if not title_elem:
            # Fallback to h2 near the names
            title_elem = soup.find("h2", class_=re.compile(r"h6 text-black", re.I))

        if title_elem:
            profile_data["title"] = title_elem.get_text(strip=True)
        
        # Extract department
        dept_elem = soup.find("div", class_="field--name-field-department-name")
        if not dept_elem:
            dept_elem = soup.find(class_=re.compile(r"department-name|field--name-field-department", re.I))
        if not dept_elem:
             # Look for specific text node "Department of" and get parent
             # This avoids capturing the entire page (which lambda on get_text() does)
             dept_text = soup.find(string=re.compile(r"Department of"))
             if dept_text:
                 dept_elem = dept_text.parent

        if dept_elem:
            profile_data["department"] = dept_elem.get_text(strip=True)
        
        # Extract bio/about
        # WARNING: Avoid "profile-course-description" which is a false positive
        bio_elem = soup.find("div", class_="field--name-body")
        if not bio_elem:
             # Look for specific headers like "Biography" or "About"
             for header in soup.find_all(["h2", "h3"]):
                 if header.get_text(strip=True).lower() in ["biography", "about", "bio"]:
                     # Get the next sibling or p tag
                     bio_elem = header.find_next_sibling(["div", "p"])
                     break
        
        if bio_elem:
            # Check if it's a course description false positive
            text = bio_elem.get_text(strip=True)
            if "In this course" not in text:
                 profile_data["bio"] = text[:2000]
        
        # Extract research interests (Areas of Expertise)
        interests = []
        # Try "Areas of Expertise" specific block first
        # Use exact text match + div to avoid nav links like "Search People by Areas of Expertise"
        expertise_header = soup.find("div", string=re.compile(r"^\s*Areas of Expertise\s*$"))
        
        if expertise_header:
            # The tags are usually in the next sibling div
            tags_container = expertise_header.find_next_sibling("div")
            if tags_container:
                 for tag in tags_container.find_all(class_="btn-tag-nolink"):
                     interests.append(tag.get_text(strip=True))
        
        if not interests:
            # Fallback to generic search (but be careful)
            interests_section = soup.find(class_=re.compile(r"field--name-field-research-interests", re.I))
            if interests_section:
                for item in interests_section.find_all(["li", "span", "a"]):
                     interests.append(item.get_text(strip=True))

        if interests:
            profile_data["research_interests"] = interests[:20]
        
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

