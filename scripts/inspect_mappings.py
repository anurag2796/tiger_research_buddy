import json
from rich.console import Console

console = Console()

with open("data/entity_mappings.json", "r") as f:
    data = json.load(f)

map_data = data["canonical_map"]
entities = data["canonical_entities"]

# check et al
et_al_id = map_data.get("et al.")
console.print(f"'et al.' maps to: {et_al_id}")
if et_al_id:
    console.print(entities.get(et_al_id))

# check who faculty_b1d333b7 is (it had many mappings)
console.print(f"\nChecking massive node faculty_b1d333b7:")
console.print(entities.get("faculty_b1d333b7"))

# Check blacklist failure
blacklist = ["et al", "author one"]
for name, cid in map_data.items():
    if any(b in name.lower() for b in blacklist):
        console.print(f"[red]Failed Blacklist:[/]: '{name}' -> {cid}")
