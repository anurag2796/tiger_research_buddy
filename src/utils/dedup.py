"""Faculty deduplication utilities for TigerResearchBuddy."""

import json
from collections import defaultdict
import re
from typing import List, Dict

from .db_logger import setup_db_logging

logger = setup_db_logging("Dedup")

def normalize_name(name: str) -> str:
    """Normalize a name for deduplication comparison."""
    if not name or not isinstance(name, str):
        return ""
    # Convert to lowercase, remove punctuation, strip extra whitespace
    normalized = re.sub(r'[^\w\s]', '', name.lower())
    return " ".join(normalized.split())

def deduplicate_faculty(faculty_list: List[Dict]) -> List[Dict]:
    """
    Deduplicate a list of faculty profiles based on normalized name.
    
    Merges duplicate entries by:
    - Taking the longest bio
    - Taking the union of research interests
    - Keeping the entry with the most populated fields as the base
    """
    if not faculty_list:
        return []
        
    grouped = defaultdict(list)
    for prof in faculty_list:
        name = prof.get("name", "")
        if not name:
            continue
        norm_name = normalize_name(name)
        if norm_name:
            grouped[norm_name].append(prof)
            
    deduped = []
    
    for norm_name, profs in grouped.items():
        if len(profs) == 1:
            deduped.append(profs[0])
            continue
            
        # We have duplicates. Merge them!
        
        # 1. Base profile (the one with the most keys/data)
        base_prof = max(profs, key=lambda p: len([k for k, v in p.items() if v]))
        merged = base_prof.copy()
        
        # 2. Merge bios (keep the longest)
        bios = [p.get("bio", "") for p in profs if p.get("bio")]
        if bios:
            merged["bio"] = max(bios, key=len)
            
        # 3. Merge research interests (union)
        all_interests = set()
        for p in profs:
            interests = p.get("research_interests", [])
            if isinstance(interests, list):
                all_interests.update(i for i in interests if isinstance(i, str) and i.strip())
        if all_interests:
            merged["research_interests"] = sorted(list(all_interests))
            
        # 4. Same for research_areas fallback
        all_areas = set()
        for p in profs:
            areas = p.get("research_areas", [])
            if isinstance(areas, list):
                all_areas.update(a for a in areas if isinstance(a, str) and a.strip())
        if all_areas:
            merged["research_areas"] = sorted(list(all_areas))
            
        # Pick the title/department from the one that has it if the base is missing it
        if not merged.get("title"):
             for p in profs:
                 if p.get("title"):
                     merged["title"] = p.get("title")
                     break
                     
        if not merged.get("department"):
             for p in profs:
                 if p.get("department"):
                     merged["department"] = p.get("department")
                     break
                     
        deduped.append(merged)
        
    logger.info(f"Deduplicated {len(faculty_list)} faculty down to {len(deduped)} unique entries.")
    return deduped
