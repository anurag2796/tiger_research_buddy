import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import process
from rich.console import Console

console = Console()

class EntityResolver:
    """
    Resolves entity aliases to canonical IDs to prevent graph fragmentation.
    Handles 'J. Smith' vs 'John Smith' using context-aware fuzzy matching.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.mappings_file = self.data_dir / "entity_mappings.json"
        
        # Load existing mappings or initialize
        self.canonical_map: Dict[str, str] = {}  # {alias_name: canonical_id}
        self.canonical_entities: Dict[str, Dict] = {}  # {canonical_id: {name, aliases, ...}}
        self._load_mappings()

    def _load_mappings(self):
        if self.mappings_file.exists():
            try:
                with open(self.mappings_file, 'r') as f:
                    data = json.load(f)
                    self.canonical_map = data.get("canonical_map", {})
                    self.canonical_entities = data.get("canonical_entities", {})
                console.print(f"[green]Loaded {len(self.canonical_entities)} canonical entities.[/]")
            except Exception as e:
                console.print(f"[red]Failed to load mappings: {e}[/]")

    def save_mappings(self):
        """Persist mappings to disk."""
        try:
            with open(self.mappings_file, 'w') as f:
                json.dump({
                    "canonical_map": self.canonical_map,
                    "canonical_entities": self.canonical_entities
                }, f, indent=2)
            # console.print("[dim]Saved entity mappings.[/]")
        except Exception as e:
            console.print(f"[red]Failed to save mappings: {e}[/]")

    def resolve_author(self, raw_name: str, affiliation: str = None, coauthors: List[str] = None) -> str:
        """
        Resolve a raw author name to a canonical ID.
        Returns: canonical_id (str)
        """
        if not raw_name:
            return "unknown_author"
            
        # Lowercase for blacklist checking
        lower_name = raw_name.lower().strip()
        
        # Blacklist / Cleaning
        BLACKLIST = [
            "name not provided", "not explicitly listed", "unknown", "anonymous", 
            "author one", "author two", "various authors", "research team",
            "deceased author"
        ]
        
        # If the name IS exactly a blacklist term (or close to it)
        if any(b in lower_name for b in BLACKLIST):
            return "unknown_author"
            
        # Specific fix for "et al"
        # If the name is JUST "et al" or "et al.", reject it
        if lower_name in ["et al", "et al."]:
            return "unknown_author"
            
        # Remove "et al." suffix if it exists (e.g. "Smith et al.")
        # We want to keep "Smith"
        clean_name = raw_name.replace(" et al.", "").replace(" et al", "").strip()
        
        # If cleaning resulted in empty string or just punctuation
        if not clean_name or len(clean_name) < 2:
            return "unknown_author"

        # 1. Exact Match (O(1)) using the CLEANED name
        if clean_name in self.canonical_map:
            return self.canonical_map[clean_name]

        # 2. Fuzzy Match (Context-Aware)
        # Only check expensive fuzzy match if we have existing entities
        if self.canonical_entities:
            best_match_id, score = self._find_best_fuzzy_match(clean_name, affiliation, coauthors)
            
            if score > 90:  # High confidence threshold
                # Link alias to existing canonical
                self.canonical_map[clean_name] = best_match_id
                self.canonical_entities[best_match_id]['aliases'].append(clean_name)
                # Merge metadata (naive)
                if affiliation and not self.canonical_entities[best_match_id].get('affiliation'):
                    self.canonical_entities[best_match_id]['affiliation'] = affiliation
                self.save_mappings()
                return best_match_id

        # 3. Create New Canonical Entity
        new_id = f"faculty_{uuid.uuid4().hex[:8]}"
        self.canonical_entities[new_id] = {
            "id": new_id,
            "canonical_name": clean_name,
            "aliases": [clean_name],
            "affiliation": affiliation,
            "coauthors": coauthors or []
        }
        self.canonical_map[clean_name] = new_id
        self.save_mappings()
        return new_id

    def _find_best_fuzzy_match(self, raw_name: str, affiliation: str, coauthors: List[str]) -> Tuple[str, int]:
        """
        Compare raw_name against all canonical entities.
        Returns (best_match_id, confidence_score)
        """
        # Optimization: Only compare against canonical names first to reduce search space
        # In production, use blocking/indexing. For 2k authors, linear scan is OK.
        
        candidates = []
        for entity in self.canonical_entities.values():
            # Base string similarity
            # Check against all aliases of this entity? Too slow.
            # Check against canonical name
            base_score = process.extractOne(raw_name, entity['aliases'])[1]
            
            final_score = base_score
            
            # Context Boost: Affiliation
            if affiliation and entity.get('affiliation'):
                if process.fuzz.token_set_ratio(affiliation, entity['affiliation']) > 85:
                    final_score += 10
            
            # Context Boost: Co-authors (Jaccard Index logic-ish)
            if coauthors and entity.get('coauthors'):
                common = set(coauthors) & set(entity['coauthors'])
                if common:
                    final_score += 5 * len(common)  # +5 per matching co-author
            
            candidates.append((entity['id'], min(final_score, 100)))

        if not candidates:
            return None, 0
            
        return max(candidates, key=lambda x: x[1])

    def get_canonical_name(self, canonical_id: str) -> str:
        return self.canonical_entities.get(canonical_id, {}).get("canonical_name", "Unknown")
