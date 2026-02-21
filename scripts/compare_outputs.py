import json
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

def load_data(path: str):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            
            # Check for flat faculty list (New format)
            if "faculty" in data and isinstance(data["faculty"], list) and data["faculty"]:
                return data["faculty"]
            
            # Check for nested research areas (Legacy format)
            if "research_areas" in data:
                faculty_map = {}
                for area in data["research_areas"]:
                    for fac in area.get("faculty", []):
                        if "name" in fac:
                            faculty_map[fac["name"]] = fac
                return list(faculty_map.values())

            # Check for checkpoint format
            if "scraped_data" in data and isinstance(data["scraped_data"], list):
                return data["scraped_data"]
                
            return []
    except FileNotFoundError:
        console.print(f"[red]File not found: {path}[/]")
        return []
    except json.JSONDecodeError:
        console.print(f"[red]Invalid JSON in {path}[/]")
        return []

def compare_data(legacy_path, new_path):
    console.print(f"[bold blue]🔍 Comparing Data[/]")
    console.print(f"Legacy: [dim]{legacy_path}[/]")
    console.print(f"New:    [dim]{new_path}[/]\n")

    legacy_faculty = load_data(legacy_path)
    new_faculty = load_data(new_path)

    legacy_map = {f.get("name"): f for f in legacy_faculty if f.get("name")}
    new_map = {f.get("name"): f for f in new_faculty if f.get("name")}

    # 1. Count Comparison
    table = Table(title="📊 Dataset Size Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Legacy", style="magenta")
    table.add_column("New (SmartCrawler)", style="green")
    table.add_column("Difference", style="yellow")

    diff = len(new_faculty) - len(legacy_faculty)
    diff_str = f"+{diff}" if diff > 0 else str(diff)
    
    table.add_row("Total Profiles", str(len(legacy_faculty)), str(len(new_faculty)), diff_str)
    console.print(table)
    console.print("\n")

    # 2. Overlap Analysis
    legacy_names = set(legacy_map.keys())
    new_names = set(new_map.keys())
    
    missing_in_new = legacy_names - new_names
    new_unique = new_names - legacy_names
    
    console.print(f"[bold]Overlap Analysis:[/]")
    console.print(f"Common Profiles: {len(legacy_names & new_names)}")
    console.print(f"Unique to Legacy: {len(missing_in_new)}")
    if missing_in_new:
        console.print(f"[dim red]Missing: {', '.join(list(missing_in_new)[:5])}...[/]")
    console.print(f"Unique to New:    {len(new_unique)}")
    if new_unique:
        console.print(f"[dim green]New: {', '.join(list(new_unique)[:5])}...[/]")
    console.print("\n")

    # 3. Quality Check (Fields per profile)
    common_names = legacy_names & new_names
    if not common_names:
        console.print("[red]No common profiles to compare quality![/]")
        return

    field_stats = {"legacy": {}, "new": {}}
    fields_to_check = ["email", "title", "department", "bio", "research_interests", "publications"]

    for name in common_names:
        leg = legacy_map[name]
        nw = new_map[name]
        
        for field in fields_to_check:
            # Check presence
            if leg.get(field):
                field_stats["legacy"][field] = field_stats["legacy"].get(field, 0) + 1
            if nw.get(field):
                field_stats["new"][field] = field_stats["new"].get(field, 0) + 1

    q_table = Table(title="✨ Data Quality (Common Profiles)")
    q_table.add_column("Field", style="cyan")
    q_table.add_column("Legacy Count", style="magenta")
    q_table.add_column("New Count", style="green")
    
    for field in fields_to_check:
        q_table.add_row(
            field, 
            str(field_stats["legacy"].get(field, 0)), 
            str(field_stats["new"].get(field, 0))
        )
    console.print(q_table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", default="data/rit_data.json", help="Path to legacy data")
    parser.add_argument("--new", default="data/restricted/rit_data_restricted.json", help="Path to new data")
    args = parser.parse_args()
    
    compare_data(args.legacy, args.new)
