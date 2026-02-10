import json
from bs4 import BeautifulSoup
import re
from rich.console import Console

console = Console()

def check_and_debug():
    # 1. Check JSON
    with open("data/rit_data.json", "r") as f:
        data = json.load(f)
    
    found = None
    for fac in data["faculty"]:
        if "Kinsman" in fac["name"]:
            found = fac
            break
            
    console.print("\n[bold]Current JSON Data for Kinsman:[/]")
    if found:
        console.print(json.dumps(found, indent=2))
    else:
        console.print("[red]Not found in JSON[/]")

    # 2. Debug Parsing (Department & Bio)
    console.print("\n[bold]Debugging Parsing (kinsman.html):[/]")
    with open("kinsman.html", "r") as f:
        soup = BeautifulSoup(f.read(), "lxml")
        
    # Department
    console.print("[bold]--- Department ---[/]")
    dept_elem = soup.find("div", class_="field--name-field-department-name")
    console.print(f"Selector 1 (div.field--name-field-department-name): {dept_elem}")
    
    if not dept_elem:
        dept_elem = soup.find(class_=re.compile(r"department-name|field--name-field-department", re.I))
        console.print(f"Selector 2 (regex): {str(dept_elem)[:200]}...")
        if dept_elem:
             console.print(f"Text content: {dept_elem.get_text(strip=True)[:200]}...")

    # Bio
    console.print("\n[bold]--- Bio ---[/]")
    bio_elem = soup.find("div", class_="field--name-body")
    console.print(f"Bio Div: {bio_elem is not None}")
    if bio_elem:
        text = bio_elem.get_text(strip=True)
        console.print(f"Bio Text starts with: {text[:50]}...")
        console.print(f"Contains 'In this course': {'In this course' in text}")


if __name__ == "__main__":
    check_and_debug()
