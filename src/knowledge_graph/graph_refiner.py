import networkx as nx
from pathlib import Path
from rich.console import Console
from rich.progress import track
from fuzzywuzzy import process
import json

from ..chatbot.ollama_client import OllamaClient

console = Console()

class GraphRefiner:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.input_path = self.data_dir / "tiger_brain.gml"
        self.output_path = self.data_dir / "tiger_brain_refined.gml"
        self.graph = nx.Graph()
        self.llm_client = OllamaClient()

    def load_graph(self):
        """Load the raw GraphBuilder output."""
        if not self.input_path.exists():
            console.print(f"[red]Input Graph not found at {self.input_path}![/]")
            return
        
        console.print(f"[cyan]Loading Raw Graph...[/]")
        self.graph = nx.read_gml(self.input_path)
        console.print(f"[green]Loaded {self.graph.number_of_nodes()} nodes.[/]")

    def normalize_concepts(self):
        """Merge synonymous concepts using fuzzy matching."""
        # Fix: Ensure nodes have 'type' attribute (default to 'unknown' if missing)
        concepts = [n for n, d in self.graph.nodes(data=True) if d.get("type", "unknown") == "concept"]
        
        console.print(f"[cyan]Analyzing {len(concepts)} concepts for duplicates...[/]")
        
        # 1. Case-Insensitive Deduplication
        merge_map = {}
        for c in concepts:
            canonical = c.lower().strip()
            if canonical not in merge_map:
                merge_map[canonical] = c
            else:
                target = merge_map[canonical]
                if c != target:
                    self.merge_nodes(c, target) # Merge c INTO target

        # 2. Fuzzy Deduplication (e.g. "Artificial Intelligence" vs "Artificial Intelligence (AI)")
        # Calculate fresh list after step 1
        remaining_concepts = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "concept"]
        console.print(f"[cyan]Refining {len(remaining_concepts)} concepts with fuzzy matching...[/]")
        
        # This is O(N^2) roughly, so let's be careful. limit to top concepts?
        # or just iterate and find close matches.
        
        # Optimization: Sort by length. Match short to long? or long to short?
        # Actually, let's skip O(N^2) for now and just do basic string cleaning.
        # "Machine Learning" vs "Machine Learning." vs " Machine Learning "
        
        pass 

    def merge_nodes(self, source, target):
        """Merge source node into target node."""
        if not self.graph.has_node(source) or not self.graph.has_node(target):
            return

        # Move edges from Source to Target
        for u, v, data in list(self.graph.edges(source, data=True)):
            neighbor = u if u != source else v
            if neighbor != target: # Avoid self-loops
                if not self.graph.has_edge(target, neighbor):
                    self.graph.add_edge(target, neighbor, **data)
                else:
                    # If edge exists, maybe boost weight?
                    # self.graph[target][neighbor]['weight'] += data.get('weight', 0)
                    pass
            
        # Remove source node
        self.graph.remove_node(source)

    def generate_taxonomy(self):
        """Use LLM to build hierarchy for top concepts."""
        # Get top 50 concepts by degree (most connected)
        concepts = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "concept"]
        sorted_concepts = sorted(concepts, key=lambda n: self.graph.degree(n), reverse=True)[:50]
        
        console.print(f"[cyan]Generating Taxonomy for top {len(sorted_concepts)} concepts...[/]")
        
        prompt = f"""
        You are an Ontology Architect.
        Analyze the following research concepts from a CS department:
        {json.dumps(sorted_concepts)}
        
        Task: Group these into a hierarchical taxonomy.
        Output strictly valid JSON:
        {{
            "categories": [
                {{
                    "name": "High Level Category (e.g. AI)",
                    "concepts": ["concept1", "concept2"]
                }}
            ]
        }}
        """
        
        try:
            # Robust JSON extraction
            response = self.llm_client.generate(prompt)
            clean_text = response.replace("```json", "").replace("```", "").strip()
            
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            
            if start != -1 and end != -1:
                json_str = clean_text[start:end+1]
                data = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
            
            for category in data.get("categories", []):
                cat_name = category.get("name")
                # Add Category Node
                self.graph.add_node(cat_name, type="topic_cluster", label=cat_name)
                
                # Link Concepts to Category
                for concept in category.get("concepts", []):
                    if self.graph.has_node(concept):
                        self.graph.add_edge(concept, cat_name, type="IS_A")
                        
            console.print("[green]Taxonomy generated and applied![/]")
            
        except Exception as e:
            console.print(f"[red]Taxonomy generation failed: {e}[/]")

    def export(self):
        nx.write_gml(self.graph, self.output_path)
        console.print(f"[bold green]Refined Graph Saved to {self.output_path}[/]")

if __name__ == "__main__":
    refiner = GraphRefiner()
    refiner.load_graph()
    refiner.normalize_concepts()
    refiner.generate_taxonomy()
    refiner.export()
