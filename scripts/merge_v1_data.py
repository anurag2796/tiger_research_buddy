import json
from pathlib import Path
from rich.console import Console

console = Console()
DATA_DIR = Path(__file__).parent.parent / "data"

def merge_datasets():
    v1_path = DATA_DIR / "rit_data.json"
    v2_path = DATA_DIR / "rit_data_v2.json"
    
    if not v1_path.exists() or not v2_path.exists():
        console.print("[red]Missing one of the data files. Check data/ directory.[/]")
        return
        
    console.print(f"Loading {v1_path.name} (V1)...")
    with open(v1_path) as f:
        v1_data = json.load(f)
        
    console.print(f"Loading {v2_path.name} (V2)...")
    with open(v2_path) as f:
        v2_data = json.load(f)
        
    v1_faculty = v1_data.get("faculty", [])
    v1_areas = v1_data.get("research_areas", [])
    v2_faculty = v2_data.get("faculty", [])
    
    # Create lookup table using lowercased name
    v1_lookup = {
        f.get("name", "").lower().strip(): f 
        for f in v1_faculty if f.get("name")
    }
    
    merged_count = 0
    
    for v2_fac in v2_faculty:
        name = v2_fac.get("name", "").lower().strip()
        if not name:
            continue
            
        # If this person was in V1, patch in the lost fields
        if name in v1_lookup:
            v1_match = v1_lookup[name]
            
            # 1. College (dropped entirely in V2 crawl)
            if v1_match.get("college") and not v2_fac.get("college"):
                v2_fac["college"] = v1_match["college"]
                
            # 2. Structured Research Areas (dropped in V2 crawl)
            if v1_match.get("research_areas") and not v2_fac.get("research_areas"):
                v2_fac["research_areas"] = v1_match["research_areas"]
                
            # 3. Bio string (V1 often had cleaner bios)
            v2_bio = v2_fac.get("bio") or ""
            if v1_match.get("bio") and len(v1_match["bio"]) > len(v2_bio):
                v2_fac["bio"] = v1_match["bio"]
                
            merged_count += 1

    # Overwrite V2 with the enriched data
    with open(v2_path, "w") as f:
        # Instead of just writing faculty, let's keep the structured format of V1
        # which included global research areas that map to the faculty references.
        output_data = {
            "crawled_at": v1_data.get("crawled_at", "Unknown"),
            "research_areas": v1_areas,
            "faculty": v2_faculty
        }
        json.dump(output_data, f, indent=2)
        
    console.print(f"[bold green]Successfully merged data for {merged_count} faculty members into V2![/]")
    console.print(f"[dim]Note: {v1_path.name} also contains {len(v1_areas)} global research area definitions.[/dim]")

if __name__ == "__main__":
    merge_datasets()
