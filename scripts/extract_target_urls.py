import json
import os
from pathlib import Path

# Target professors
TARGET_NAMES = [
    "Thomas Kinsman",
    "Mohan Kumar",
    "Qiuxiao Chen",
    "Dukka KC",
    "Matthew Fluet"
]

DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "rit_data.json"
OUTPUT_FILE = DATA_DIR / "target_urls.json"

def main():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    target_urls = {}
    
    # Flatten all faculty
    all_faculty = []
    
    # 1. From research_areas
    for area in data.get("research_areas", []):
         if "faculty" in area:
            all_faculty.extend(area["faculty"])

    # Dedup
    unique_faculty = {}
    for f in all_faculty:
        name = f.get("name", "").strip()
        url = f.get("url", "")
        if name and url:
             unique_faculty[name] = url
             
    print(f"Total unique faculty found in rit_data.json: {len(unique_faculty)}")

    # Find targets
    found_targets = []
    
    # Normalize names for comparison
    def normalize(n):
        return n.lower().replace("dr.", "").replace("professor", "").strip()

    for target in TARGET_NAMES:
        target_norm = normalize(target)
        found = False
        
        for name, url in unique_faculty.items():
            if target_norm in normalize(name):
                target_urls[target] = url
                found_targets.append(target)
                print(f"MATCH: {target} -> {url}")
                found = True
                break
        
        if not found:
            print(f"MISSING: {target} - searching harder...")
            # Hard fallback or manual construction?
            # RIT directory URLs are predictable: https://www.rit.edu/computing/directory/[uid]-[name]
            # Since we don't have the UID, we can't construct it perfectly. 
            # We will use a placeholder or try to find it in other sources if possible.
            # For now, just mark as missing.

    # Fill up with additional CS professors
    # Look for "Computer Science" keyword in area/department if available, or just random
    
    # We want 10 total
    needed = 10 - len(target_urls)
    
    if needed > 0:
        count = 0
        for name, url in unique_faculty.items():
            if count >= needed:
                break
            
            # Check if likely CS (heuristic)
            # We don't have department info in this simple list, so we take what we can get
            # But we avoid adding the targets again
            is_target = False
            for t in TARGET_NAMES:
                if normalize(t) in normalize(name):
                    is_target = True
                    break
            
            if not is_target and url not in target_urls.values():
                key = f"Additional_{count+1}_{name}"
                target_urls[key] = url
                count += 1
                print(f"Added additional: {name}")

    # Output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(target_urls, f, indent=2)
    
    print(f"Saved {len(target_urls)} URLs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
