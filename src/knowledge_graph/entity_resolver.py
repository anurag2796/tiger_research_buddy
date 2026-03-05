import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from fuzzywuzzy import process, fuzz
import jellyfish  # For phonetic matching
import networkx as nx
from rich.console import Console
from ..utils.schema import Faculty, Publication

console = Console()

class EntityResolver:
    """
    Resolves entity aliases to canonical IDs to prevent graph fragmentation.
    Handles 'J. Smith' vs 'John Smith' using context-aware fuzzy matching.
    """
    
    def __init__(self, data_dir: Path, graph: Optional[nx.DiGraph] = None,
                 jaccard_threshold: float = 0.4):
        self.data_dir = data_dir
        self.mappings_file = self.data_dir / "entity_mappings.json"
        self.graph = graph
        self.jaccard_threshold = jaccard_threshold
        
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
        except Exception as e:
            console.print(f"[red]Failed to save mappings: {e}[/]")

    def _is_valid_name(self, name: str) -> bool:
        """Check if name is valid and not a blacklist term."""
        if not name:
            return False
            
        lower_name = name.lower().strip()
        
        BLACKLIST = [
            "name not provided", "not explicitly listed", "unknown", "anonymous", 
            "author one", "author two", "various authors", "research team",
            "deceased author", "et al", "et al."
        ]
        
        if any(b in lower_name for b in BLACKLIST):
            return False
            
        if len(lower_name) < 2:
            return False
            
        return True

    def _clean_name(self, name: str) -> str:
        """Clean author name."""
        clean = name.replace(" et al.", "").replace(" et al", "").strip()
        # Remove titles
        titles = ["Dr.", "Prof.", "Mr.", "Ms.", "Mrs.", "PhD"]
        for t in titles:
            if clean.startswith(t):
                clean = clean[len(t):].strip()
        return clean

    def _phonetic_match(self, name1: str, name2: str) -> bool:
        """Check if two names sound similar using Metaphone."""
        try:
            return jellyfish.metaphone(name1) == jellyfish.metaphone(name2)
        except:
            return False

    # --- Graph-Context Helpers (Relational-Aware Resolution) ---

    def _get_neighbor_ids(self, node_name: str) -> Set[str]:
        """Return the set of 1-hop neighbor node IDs from the attached graph."""
        if self.graph is None or node_name not in self.graph:
            return set()
        return set(self.graph.neighbors(node_name))

    @staticmethod
    def _jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
        """Standard Jaccard index: |A ∩ B| / |A ∪ B|."""
        if not set_a and not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    def resolve_faculty(self, raw_name: str, department: str = None) -> str:
        """
        Resolve a faculty name to a canonical ID with advanced matching.
        """
        if not self._is_valid_name(raw_name):
            return "unknown_faculty"
            
        clean_name = self._clean_name(raw_name)
        
        # 1. Exact Match (O(1))
        if clean_name in self.canonical_map:
            return self.canonical_map[clean_name]

        # 2. Fuzzy / Phonetic / Graph-Context Match
        if self.canonical_entities:
            best_match_id, score = self._find_best_match(clean_name, department)
            canonical = self.canonical_entities[best_match_id]['canonical_name']
            
            is_match = False

            if self.graph is not None:
                # --- Relational-aware path (graph attached) ---
                # Scores above 95 auto-merge even without graph confirmation.
                if score > 95:
                    is_match = True
                elif score > 80:
                    # Ambiguous zone: let the graph topology decide.
                    neighbors_a = self._get_neighbor_ids(clean_name)
                    neighbors_b = self._get_neighbor_ids(canonical)
                    jaccard = self._jaccard_similarity(neighbors_a, neighbors_b)
                    console.print(
                        f"[dim]Graph check: {clean_name} vs {canonical} "
                        f"| Jaccard={jaccard:.2f} (threshold={self.jaccard_threshold})[/]"
                    )
                    if jaccard >= self.jaccard_threshold:
                        is_match = True
                    # else: keep distinct — graph says they're different people
            else:
                # --- Legacy path (no graph) — original thresholds preserved ---
                if score >= 85:
                    is_match = True
                elif score > 80:
                    if self._phonetic_match(clean_name, canonical):
                        is_match = True
                        console.print(f"[dim]Phonetic match found: {clean_name} ~= {canonical}[/]")

            if is_match:
                # Link alias
                self.canonical_map[clean_name] = best_match_id
                if clean_name not in self.canonical_entities[best_match_id]['aliases']:
                    self.canonical_entities[best_match_id]['aliases'].append(clean_name)
                
                # Merge Dept if missing
                if department and not self.canonical_entities[best_match_id].get('department'):
                    self.canonical_entities[best_match_id]['department'] = department
                    
                self.save_mappings()
                return best_match_id

        # 3. Create New
        new_id = f"faculty_{uuid.uuid4().hex[:8]}"
        self.canonical_entities[new_id] = {
            "id": new_id,
            "canonical_name": clean_name,
            "aliases": [clean_name],
            "department": department
        }
        self.canonical_map[clean_name] = new_id
        self.save_mappings()
        return new_id

    def _find_best_match(self, raw_name: str, department: str) -> Tuple[str, int]:
        """Find best match using weighted scoring."""
        candidates = []
        
        # Blocking: Optimization (Optional for now, straightforward loop is fine for <2k entities)
        # For huge datasets, block by first letter of last name.
        
        # Convert values to list to prevent "dictionary changed size during iteration"
        # when running in multithreaded environments (like ScholarCrawler).
        for entity in list(self.canonical_entities.values()):
            canonical = entity['canonical_name']
            
            # 1. Token Set Ratio (good for "Smith, J" vs "John Smith")
            score = fuzz.token_set_ratio(raw_name, canonical)
            
            # 2. Levenshtein Distance (for typos)
            # transform 0-100 scale: 100 - (distance / max_len * 100)
            lev_dist = jellyfish.levenshtein_distance(raw_name, canonical)
            max_len = max(len(raw_name), len(canonical))
            lev_score = 100 - (lev_dist / max_len * 100) if max_len > 0 else 0
            
            final_score = max(score, lev_score)
            
            # Context Boost: Affiliation
            if department and entity.get('department'):
                if fuzz.token_set_ratio(department, entity['department']) > 85:
                    final_score += 5  # Small boost for same department
                    
            # Special Heuristic: Force strict penalty if first names are fully written but differ.
            # Skip the penalty when either name looks like an initial (e.g. "C.", "J", "A.").
            parts_raw = raw_name.split()
            parts_can = canonical.split()
            if len(parts_raw) >= 2 and len(parts_can) >= 2:
                raw_first = parts_raw[0].lower()
                can_first = parts_can[0].lower()
                raw_is_initial = len(raw_first.rstrip('.')) <= 1
                can_is_initial = len(can_first.rstrip('.')) <= 1
                if not raw_is_initial and not can_is_initial and raw_first != can_first:
                    # Don't penalize if they are phonetically identical or highly similar (typos)
                    if not self._phonetic_match(raw_first, can_first) and fuzz.ratio(raw_first, can_first) < 80:
                        # e.g., "Christopher Kanan" != "Charles Kanan"
                        final_score = min(final_score, 60)  # Penalty ensures they don't merge

            candidates.append((entity['id'], min(final_score, 100)))

        if not candidates:
            return None, 0
            
        return max(candidates, key=lambda x: x[1])

    def resolve_publication(self, title: str, authors: List[str]) -> str:
        """
        Deduplicate publications based on title similarity.
        Returns a simplified hash-like ID for deduplication.
        """
        # We don't necessarily store a persistent map for pub IDs 
        # unless we want global pub resolution.
        # For now, let's normalize the title.
        
        clean_title = title.lower().strip()
        # Remove punctuation
        import string
        clean_title = clean_title.translate(str.maketrans('', '', string.punctuation))
        
        # Return a hash of valid title
        return f"pub_{uuid.uuid5(uuid.NAMESPACE_DNS, clean_title).hex[:12]}"
