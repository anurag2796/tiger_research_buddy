from typing import List, Dict, Any, Optional
import networkx as nx
import json
import random

class EntityExtractor:
    """
    Hybrid entity extraction: Fast lexical matching with LLM fallback.
    
    Strategy 1: Use lexical matching by default (1ms), only invoke LLM 
    when results are sparse (<2 entities).
    """
    def __init__(self, graph: nx.Graph, enable_llm_fallback: bool = True, threshold: int = 2):
        self.graph = graph
        self.enable_llm_fallback = enable_llm_fallback
        self.threshold = threshold  # Min entities before triggering LLM
        self._build_index()
        
        # Lazy load LLM client (only if fallback enabled)
        self.llm_client = None
        if self.enable_llm_fallback:
            try:
                from ..chatbot.ollama_client import get_ollama_client
                self.llm_client = get_ollama_client()
            except Exception as e:
                # Gracefully degrade to lexical-only mode
                self.enable_llm_fallback = False
                print(f"Warning: LLM fallback disabled: {e}")

    def _build_index(self):
        """
        Pre-compute a lowercase lookup index mapping labels to node IDs.
        Handles aliases if available.
        """
        self.index = {}
        for node, data in self.graph.nodes(data=True):
            # Priority 1: Try 'name' attribute (used for concepts)
            label = data.get('name', '')
            
            # Priority 2: Try 'label' attribute
            if not label:
                label = data.get('label', '')
            
            # Fallback: If no label, use the node ID itself (if it's a string)
            if not label and isinstance(node, str):
                label = node
                
            if label:
                self.index[str(label).lower()] = node
            
            # Index aliases if they exist (from our EntityResolver!)
            if 'aliases' in data:
                # Aliases might be a list or a string depending on GML import
                aliases = data['aliases']
                if isinstance(aliases, list):
                    for alias in aliases:
                        self.index[alias.lower()] = node
                elif isinstance(aliases, str):
                     self.index[aliases.lower()] = node

        # Build Token Index for Fuzzy Matching
        # Maps "ororbia" -> [node_id, node_id]
        self.token_index = {}
        for label, node_id in self.index.items():
            tokens = label.split()
            for t in tokens:
                if len(t) < 4: continue # Skip short words
                if t not in self.token_index:
                    self.token_index[t] = []
                self.token_index[t].append(node_id)

    def extract(self, query: str) -> List[Dict[str, Any]]:
        """
        Strategy 1: Fast lexical matching with LLM fallback.
        
        Returns: List of entity dicts with keys: id, label, type
        """
        # Step 1: Try lexical matching (fast path)
        entities = self._lexical_match(query)
        
        if not entities:
            # Step 1.5: Try partial matching (for "Kinsman", "Thoms Kinsman")
            entities = self._partial_lexical_match(query)
            
        # Step 2: If results are sparse AND LLM available, use fallback
        if len(entities) < self.threshold and self.enable_llm_fallback and self.llm_client:
            llm_entities = self._llm_fallback(query)
            # Merge, prioritizing lexical matches
            entities = self._merge_entities(entities, llm_entities)
        
        return entities

    def _lexical_match(self, query: str) -> List[Dict[str, Any]]:
        """
        Pure lexical matching against graph index.
        Original fast matching logic.
        """
        import string
        
        # Strip punctuation for better matching
        query_cleaned = query.translate(str.maketrans('', '', string.punctuation))
        query_lower = query_cleaned.lower()
        found_entities = []
        
        # Naive token matching
        for label, node_id in self.index.items():
            if f" {label} " in f" {query_lower} ":
                 display_label = (
                     self.graph.nodes[node_id].get('name') or 
                     self.graph.nodes[node_id].get('label') or 
                     label
                 )
                 found_entities.append({
                     "id": node_id,
                     "label": display_label,
                     "type": self.graph.nodes[node_id].get('type', 'unknown')
                 })
        
        # Deduplicate by ID
        unique_map = {}
        for e in found_entities:
            unique_map[e['id']] = e
            
        return list(unique_map.values())

    def _partial_lexical_match(self, query: str) -> List[Dict[str, Any]]:
        """
        Fuzzy token matching (Handles typos like 'Orobia' -> 'Ororbia').
        """
        import string
        from difflib import get_close_matches
        
        # Clean query
        query_cleaned = query.translate(str.maketrans('', '', string.punctuation))
        query_tokens = [t for t in query_cleaned.lower().split() if len(t) > 3]
        
        found_ids = set()
        
        if not query_tokens:
            return []
            
        # 1. Exact Token Match (e.g. "Kinsman" in "Thomas Kinsman")
        for qt in query_tokens:
            if qt in self.token_index:
                found_ids.update(self.token_index[qt])
                
        # 2. Fuzzy Token Match
        all_tokens = list(self.token_index.keys())
        for qt in query_tokens:
            matches = get_close_matches(qt, all_tokens, n=3, cutoff=0.8)
            for m in matches:
                found_ids.update(self.token_index[m])
        
        # Hydrate entities and Calculate Confidence Scores
        from difflib import SequenceMatcher
        
        found_entities = []
        for node_id in found_ids:
            label = self.graph.nodes[node_id].get('name') or self.graph.nodes[node_id].get('label') or str(node_id)
            label_tokens = label.lower().split()
            
            # Calculate Score: Average best token match
            # For every query token, find the best matching token in the label
            token_scores = []
            for qt in query_tokens:
                best_token_score = 0.0
                for lt in label_tokens:
                    # Use ratio() for similarity
                    score = SequenceMatcher(None, qt, lt).ratio()
                    if score > best_token_score:
                        best_token_score = score
                token_scores.append(best_token_score)
            
            # Final Score is average of token scores (so "Kinsman" -> "Thomas Kinsman" is 1.0 if "Kinsman" is in it)
            # Wait, if query is "Kinsman", matches "Thomas Kinsman":
            # "Kinsman" matches "Kinsman" (1.0). Avg = 1.0. Correct.
            # Query "Tom Kinsman": "Tom"~"Thomas" (0.xxx), "Kinsman"~"Kinsman" (1.0). Avg ~0.9.
            avg_score = sum(token_scores) / len(token_scores) if token_scores else 0.0
            
            # Boost exact substring/full matches
            if query.lower() in label.lower():
                avg_score = max(avg_score, 1.0) # Exact substring is perfect confidence
            
            found_entities.append({
                "id": node_id,
                "label": label,
                "type": self.graph.nodes[node_id].get('type', 'unknown'),
                "match_quality": "partial",
                "score": round(avg_score, 2)
            })
                  
        # Prioritize by Type AND Score
        def sort_key(e):
            # Type Score (0-3) + Confidence Score (0-1)
            t_score = 0
            t = e['type'].lower()
            if t in ['faculty', 'person']: t_score = 3
            elif t in ['concept', 'topic']: t_score = 2
            elif t in ['paper', 'publication']: t_score = 1
            
            return (t_score, e['score'])
            
        found_entities.sort(key=sort_key, reverse=True)
                 
        # Limit results (avoid returning 1000 'Smiths')
        return found_entities[:10]
    
    def _llm_fallback(self, query: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract entities when lexical matching fails.
        """
        entity_samples = self._get_entity_samples()
        
        prompt = f"""Extract research entities from this query.

Query: "{query}"

Our graph has {len(self.index)} entities. Sample:
{entity_samples}

Extract the most relevant entity names. Consider synonyms ("CNNs" = "Convolutional Neural Networks").

Return ONLY a JSON array of strings:
["Entity 1", "Entity 2"]

JSON:"""

        try:
            # Use generate() with custom system prompt to avoid persona injection
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a research entity extraction assistant. Extract entities accurately from queries."
            )
            response_clean = response.strip()
            
            # Parse JSON
            if '[' in response_clean and ']' in response_clean:
                start = response_clean.find('[')
                end = response_clean.rfind(']') + 1
                entity_names = json.loads(response_clean[start:end])
                return self._fuzzy_match_entities(entity_names)
            
            return []
        except Exception as e:
            print(f"LLM fallback failed: {e}")
            return []
    
    def _get_entity_samples(self) -> str:
        """Get sample entities for LLM prompt."""
        faculty, concepts = [], []
        
        for node, data in list(self.graph.nodes(data=True))[:200]:
            node_type = data.get('type', '')
            label = data.get('name') or data.get('label', str(node))
            
            if node_type == 'faculty' and len(faculty) < 10:
                faculty.append(label)
            elif node_type == 'concept' and len(concepts) < 30:
                concepts.append(label)
        
        samples = []
        if faculty:
            samples.append(f"Faculty: {', '.join(faculty)}")
        if concepts:
            samples.append(f"Concepts: {', '.join(concepts[:20])}")
        
        return "\n".join(samples)
    
    def _fuzzy_match_entities(self, entity_names: List[str]) -> List[Dict[str, Any]]:
        """
        Fuzzy match LLM results against graph index.
        """
        from difflib import get_close_matches
        
        matched = []
        for name in entity_names:
            name_lower = name.lower()
            
            # Exact match first
            if name_lower in self.index:
                node_id = self.index[name_lower]
                matched.append({
                    "id": node_id,
                    "label": self.graph.nodes[node_id].get('name') or name,
                    "type": self.graph.nodes[node_id].get('type', 'unknown')
                })
            else:
                # Fuzzy matching
                close_matches = get_close_matches(name_lower, self.index.keys(), n=1, cutoff=0.75)
                if close_matches:
                    node_id = self.index[close_matches[0]]
                    matched.append({
                        "id": node_id,
                        "label": self.graph.nodes[node_id].get('name') or name,
                        "type": self.graph.nodes[node_id].get('type', 'unknown')
                    })
        
        return matched
    
    def _merge_entities(self, lexical: List[Dict], llm: List[Dict]) -> List[Dict]:
        """Merge lexical and LLM results, prioritizing lexical."""
        merged = {}
        for e in lexical:
            merged[e['id']] = e
        for e in llm:
            if e['id'] not in merged:
                merged[e['id']] = e
        return list(merged.values())
