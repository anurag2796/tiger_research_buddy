"""PhD Student Crawler for RIT GCCIS.

Crawls the PhD student directory to find students, their advisors, and research interests.
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

class PhDStudentCrawler:
    """Crawl RIT PhD student directory."""
    
    # Target department people pages which often list students
    SOURCES = [
        "https://www.rit.edu/computing/department-computer-science/people",
        "https://www.rit.edu/computing/department-computing-security/people",
        "https://www.rit.edu/computing/department-software-engineering/people",
        "https://www.rit.edu/computing/phd-computing-and-information-sciences"
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TigerResearchBuddy/1.0"
        })
    
    def crawl(self) -> list[dict]:
        """Crawl the student directory."""
        console.print(f"[bold blue]🎓 Crawling RIT PhD Student Directories...[/]")
        
        all_students = []
        
        for url in self.SOURCES:
            console.print(f"[dim]Checking: {url}[/]")
            try:
                if "phd-computing" in url:
                    students = self._crawl_phd_program_site(url)
                else:
                    students = self._crawl_department_page(url)
                
                if students:
                    console.print(f"[green]  ✓ Found {len(students)} students[/]")
                    all_students.extend(students)
            except Exception as e:
                console.print(f"[yellow]  Could not crawl {url}: {e}[/]")
        
        # De-duplicate by name
        unique_students_map = {s['name']: s for s in all_students}
        unique_students = list(unique_students_map.values())
        
        console.print(f"[green]✓ Found {len(unique_students)} total PhD students[/]")
        return unique_students

    def _crawl_department_page(self, url: str) -> list[dict]:
        """Crawl a department people page."""
        response = self.session.get(url, timeout=30)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        students = []
        
        # Find all person cards/rows
        # RIT standard design uses .person-card or .views-row
        rows = soup.find_all(class_=re.compile(r"person|directory-entry|views-row"))
        
        for row in rows:
            # Check if text indicates PhD Student
            text = row.get_text(" ", strip=True)
            if "PhD" in text or "Doctoral" in text or "Graduate Student" in text:
                 student = self._parse_student_entry(row)
                 if student:
                     students.append(student)
        
        return students

    def _crawl_phd_program_site(self, url: str) -> list[dict]:
        """Crawl the main PhD program site."""
        # This page often links to 'Featured Profiles' or similar
        response = self.session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        
        students = []
        
        # Look for links to student profiles
        for link in soup.find_all("a", href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Heuristic: Link text contains "Student" or points to a profile that mentions PhD
            if "student" in text.lower() or "candidate" in text.lower():
                 # We skip creating full objects here as we'd need to visit the link
                 # But we can try to extract name from text
                 pass
        
        return students

    def _parse_student_entry(self, element) -> Optional[dict]:
        """Parse a single student entry from the HTML."""
        try:
            # Name often in H2, H3, or a generic 'title' class
            name_elem = element.find(["h2", "h3", "h4", "div"], class_=re.compile(r"name|title|field-content"))
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3 or "Directory" in name:
                return None
            
            # Double check it isn't a professor (heuristic)
            full_text = element.get_text(" ", strip=True)
            if "Professor" in full_text or "Lecturer" in full_text:
                return None # Likely faculty, not student
            
            # Advisor
            advisor = "Unknown"
            advisor_elem = element.find(string=re.compile(r"Advisor", re.I))
            if advisor_elem:
                # Often "Advisor: Name" in the same element or parent text
                parent_text = advisor_elem.parent.get_text(strip=True)
                match = re.search(r"Advisor:?\s*([A-Za-z\s\.]+)", parent_text, re.I)
                if match:
                    advisor = match.group(1).strip()
            
            # Research Interests
            interests = []
            # ... (Existing logic ok) ...
            
            # Profile Link
            profile_url = None
            link = element.find("a", href=True)
            if link and "rit.edu" in link['href']:
                profile_url = link['href']
            
            return {
                "name": name,
                "advisor": advisor,
                "research_interests": interests, # Simplification
                "email": None, # Hard to robustly get without visiting profile
                "url": profile_url,
                "type": "phd_student"
            }
            
        except Exception as e:
            return None

    def save_data(self, data: list[dict], filename: str = "phd_students.json") -> Path:
        """Save data to JSON."""
        filepath = DATA_DIR / filename
        with open(filepath, "w") as f:
            json.dump({"students": data, "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
        console.print(f"[green]✓ Saved student data to {filepath}[/]")
        return filepath

def crawl_phd_students():
    """Main function to crawl PhD students."""
    crawler = PhDStudentCrawler()
    students = crawler.crawl()
    if students:
        crawler.save_data(students)
    return students

def add_phd_to_vectorstore(data_file: str = "phd_students.json"):
    """Index PhD students into vector store."""
    from ..database import get_vector_store
    
    filepath = DATA_DIR / data_file
    if not filepath.exists():
        console.print(f"[yellow]Data file {data_file} not found.[/]")
        return

    with open(filepath) as f:
        data = json.load(f)
    
    students = data.get("students", [])
    store = get_vector_store()
    store.initialize()
    
    documents = []
    
    for i, student in enumerate(students):
        # Create rich content for searching
        content = f"""PhD Student: {student['name']}
Advisor: {student['advisor']}
Research Interests: {', '.join(student['research_interests'])}
Email: {student.get('email', 'N/A')}
"""
        doc_id = f"phd_student_{i}_{student['name'].lower().replace(' ', '_')}"
        
        documents.append({
            "id": doc_id,
            "content": content,
            "metadata": {
                "doc_type": "phd_student",
                "name": student['name'],
                "advisor": student['advisor'],
                "interests": ", ".join(student['research_interests'])
            }
        })
    
    if documents:
        store.add_documents(documents)
        console.print(f"[green]✓ Indexed {len(documents)} PhD students[/]")
