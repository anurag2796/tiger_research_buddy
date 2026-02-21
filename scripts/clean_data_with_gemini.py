import json
import uuid
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from fuzzywuzzy import fuzz, process

# Add src to path
sys.path.append(".")
from src.utils.gemini_client import GeminiClient

console = Console()

DATA_DIR = Path("data")
RIT_DATA_FILE = DATA_DIR / "rit_data_v2.json"
MAPPINGS_FILE = DATA_DIR / "entity_mappings.json"
CLEAN_MAPPINGS_FILE = DATA_DIR / "entity_mappings_cleaned.json"

def load_json(path):
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    if not RIT_DATA_FILE.exists():
        console.print(f"[red]RIT Data file not found at {RIT_DATA_FILE}[/]")
        return

    # 1. Load Source of Truth
    rit_data = load_json(RIT_DATA_FILE)
    faculty_list = rit_data.get("faculty", [])
    valid_faculty_names = {f.get("name").strip() for f in faculty_list if f.get("name")}
    
    console.print(f"[green]Loaded {len(valid_faculty_names)} valid faculty names from RIT Data.[/]")

    # 2. Load Existing Mappings
    mappings_data = load_json(MAPPINGS_FILE)
    old_map = mappings_data.get("canonical_map", {})
    old_entities = mappings_data.get("canonical_entities", {})
    
    console.print(f"[dim]Loaded {len(old_map)} existing aliases and {len(old_entities)} entities.[/]")

    # 3. Initialize New Structures
    new_map = {}
    new_entities = {}
    
    # Helper to get or create ID for a faculty name
    name_to_id = {} # valid_name -> uuid

    # 4. Bootstrap Valid Entities from Source of Truth
    console.print("[bold blue]Bootstrapping valid entities...[/]")
    
    # Check if old entities match valid faculty
    for eid, entity_data in old_entities.items():
        cname = entity_data.get("canonical_name", "")
        if cname in valid_faculty_names:
            # Preserve existing ID for continuity
            name_to_id[cname] = eid
            new_entities[eid] = entity_data
            new_entities[eid]['aliases'] = [cname] # Reset aliases, we will add back valid ones
            new_map[cname] = eid
            
    # Create entries for missing faculty
    for fname in valid_faculty_names:
        if fname not in name_to_id:
            new_id = f"faculty_{uuid.uuid4().hex[:8]}"
            name_to_id[fname] = new_id
            new_entities[new_id] = {
                "id": new_id,
                "canonical_name": fname,
                "aliases": [fname],
                "department": "Golisano College" # Default/Placeholder
            }
            new_map[fname] = new_id

    # 5. Identify Orphan Aliases
    # These are keys in old_map that are NOT exact matches for valid faculty names
    orphan_aliases = []
    for alias, eid in old_map.items():
        if alias not in valid_faculty_names:
             orphan_aliases.append(alias)
             
    console.print(f"[yellow]Found {len(orphan_aliases)} orphan aliases to verify.[/]")
    
    # 6. Apply Gemini Cleaning (Batch Process)
    client = GeminiClient()
    
    # We will process in chunks of 10 to avoid token limits
    chunk_size = 10
    processed_aliases = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Cleaning aliases with Gemini...", total=len(orphan_aliases))
        
        for i in range(0, len(orphan_aliases), chunk_size):
            chunk = orphan_aliases[i:i+chunk_size]
            
            prompt = f"""
            You are a data cleaning assistant for an academic knowledge graph.
            I have a list of strings that might be aliases for faculty members, or they might be concepts/improper data.
            
            Valid Faculty Names: {list(valid_faculty_names)}
            
            Analyze these candidate aliases:
            {json.dumps(chunk)}
            
            For each alias, determine:
            1. Is it a person's name? (true/false)
            2. Does it look like an alias for a specific Valid Faculty Name? (fuzzy match). 
               Use "None" if no clear match.
            
            Return JSON list of objects:
            [
              {{"alias": "string", "is_person": bool, "match": "Faculty Name" or null}}
            ]
            """
            
            try:
                result = client.generate_json(prompt)
                
                if result and isinstance(result, list):
                    for item in result:
                        alias = item.get("alias")
                        is_person = item.get("is_person")
                        match = item.get("match")
                        
                        if alias and is_person:
                            # If it matches a valid faculty, link it
                            if match and match in name_to_id:
                                fid = name_to_id[match]
                                new_map[alias] = fid
                                if alias not in new_entities[fid]['aliases']:
                                    new_entities[fid]['aliases'].append(alias)
                                # console.print(f"[green]Linked '{alias}' -> {match}[/]")
                            else:
                                # If it's a person but no match, heuristic check
                                # Check simple fuzzy match locally as fallback
                                best_match, score = process.extractOne(alias, valid_faculty_names)
                                if score > 90:
                                    fid = name_to_id[best_match]
                                    new_map[alias] = fid
                                    new_entities[fid]['aliases'].append(alias)
                                    # console.print(f"[cyan]Fuzzy Linked '{alias}' -> {best_match} ({score})[/]")
                                else:
                                    pass
                                    # console.print(f"[dim]Dropped person/unmatched: {alias}[/]")
                        else:
                            pass
                            # console.print(f"[dim]Dropped non-person: {alias}[/]")
                            
            except Exception as e:
                console.print(f"[red]Error processing chunk: {e}[/]")
                
            processed_aliases += len(chunk)
            progress.update(task, completed=processed_aliases)
            
    # 7. Save Cleaned Data
    output_data = {
        "canonical_map": new_map,
        "canonical_entities": new_entities
    }
    save_json(CLEAN_MAPPINGS_FILE, output_data)
    console.print(f"[bold green]Cleaning Complete![/]")
    console.print(f"Saved to {CLEAN_MAPPINGS_FILE}")
    console.print(f"Total Entities: {len(new_entities)}")
    console.print(f"Total Mappings: {len(new_map)}")

if __name__ == "__main__":
    main()
