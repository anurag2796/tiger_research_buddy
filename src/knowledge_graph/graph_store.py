
import kuzu
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
from rich.console import Console

console = Console()

class GraphStore:
    """Persistent Graph Store using KuzuDB."""
    
    def __init__(self, db_path: Path, drop_existing: bool = False):
        self.db_path = db_path
        
        if drop_existing and self.db_path.exists():
            shutil.rmtree(self.db_path)
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)
        
        # Initialize Schema
        self._init_schema()
        
    def _init_schema(self):
        """Define Node and Rel tables."""
        # Nodes
        self._create_node_table("Faculty", {
            "name": "STRING", 
            "title": "STRING",
            "email": "STRING", 
            "department": "STRING",
            "research_interests": "STRING"
        }, primary_key="name")
        
        self._create_node_table("Paper", {
            "paper_id": "STRING",
            "title": "STRING",
            "year": "INT64",
            "venue": "STRING",
            "abstract": "STRING",
            "domain": "STRING",
            "novelty": "STRING",
            "outcomes": "STRING",
            "source_file": "STRING"
        }, primary_key="paper_id")
        
        self._create_node_table("Concept", {
            "concept_id": "STRING",
            "name": "STRING",
            "type": "STRING"
        }, primary_key="concept_id")
        
        self._create_node_table("Topic", {
            "topic_id": "STRING",
            "name": "STRING",
            "category": "STRING"
        }, primary_key="topic_id")
        
        # Relationships
        self._create_rel_table("Authored", "Faculty", "Paper")
        self._create_rel_table("Mentions", "Paper", "Concept")
        self._create_rel_table("CollaboratesWith", "Faculty", "Faculty", properties={"weight": "INT64"})
        self._create_rel_table("WorksOn", "Faculty", "Topic", properties={"weight": "FLOAT"})
        self._create_rel_table("About", "Paper", "Topic", properties={"weight": "FLOAT"})
        self._create_rel_table("RelatedTo", "Concept", "Concept", properties={"relation": "STRING", "weight": "FLOAT"})

    def _validate_identifier(self, name: str):
        """Ensure the identifier is a valid Cypher identifier and safe from injection."""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            raise ValueError(f"Invalid identifier: {name}")

    def _validate_type(self, type_name: str):
        """Validate KuzuDB data types."""
        allowed_types = {
            "STRING", "INT64", "INT32", "INT16", "INT8", "UINT64", "UINT32", "UINT16", "UINT8",
            "DOUBLE", "FLOAT", "BOOL", "DATE", "TIMESTAMP", "TIMESTAMP_NS", "TIMESTAMP_MS",
            "TIMESTAMP_SEC", "TIMESTAMP_TZ", "INTERVAL", "INTERNAL_ID"
        }
        if type_name.upper() not in allowed_types:
            raise ValueError(f"Invalid type: {type_name}")

    def _create_node_table(self, table_name: str, schema: Dict[str, str], primary_key: str):
        try:
            self._validate_identifier(table_name)
            self._validate_identifier(primary_key)
            # Build schema string: "name STRING, age INT64, ..."
            schema_parts = []
            for k, v in schema.items():
                self._validate_identifier(k)
                self._validate_type(v)
                schema_parts.append(f"{k} {v}")

            schema_str = ", ".join(schema_parts)
            self.conn.execute(f"CREATE NODE TABLE IF NOT EXISTS {table_name}({schema_str}, PRIMARY KEY ({primary_key}))")
        except Exception as e:
            # Re-raise ValueErrors for validation failures
            if isinstance(e, ValueError):
                raise e
            # Table might already exist
            pass

    def _create_rel_table(self, name: str, src: str, dst: str, properties: Optional[Dict[str, str]] = None):
        try:
            self._validate_identifier(name)
            self._validate_identifier(src)
            self._validate_identifier(dst)

            props_str = ""
            if properties:
                prop_parts = []
                for k, v in properties.items():
                    self._validate_identifier(k)
                    self._validate_type(v)
                    prop_parts.append(f"{k} {v}")
                props_str = ", " + ", ".join(prop_parts)
            
            self.conn.execute(f"CREATE REL TABLE IF NOT EXISTS {name}(FROM {src} TO {dst}{props_str})")
        except Exception as e:
            # Re-raise ValueErrors for validation failures
            if isinstance(e, ValueError):
                raise e
            # Table might already exist
            pass

    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a Cypher query."""
        return self.conn.execute(query, parameters)

    # --- Data Ingestion Helpers ---
    
    def add_faculty(self, faculty: Dict):
        """Add or Update Faculty Node."""
        # Kuzu supports MERGE but for bulk loading explicit logic might be safer. 
        # For now using MERGE.
        query = """
        MERGE (f:Faculty {name: $name})
        SET f.title = $title, f.email = $email, f.department = $department, f.research_interests = $research_interests
        """
        interests = faculty.get("research_interests", "")
        if isinstance(interests, list):
            interests = ", ".join(interests)

        self.conn.execute(query, {
            "name": faculty.get("name", "Unknown"),
            "title": faculty.get("title", ""),
            "email": faculty.get("email", ""),
            "department": faculty.get("department", ""),
            "research_interests": interests
        })

    def add_paper(self, paper: Dict):
        """Add Paper Node."""
        query = """
        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title, p.year = $year, p.venue = $venue, p.abstract = $abstract, 
            p.domain = $domain, p.novelty = $novelty, p.outcomes = $outcomes, p.source_file = $source_file
        """
        # Ensure year is int
        year = paper.get("year", 0)
        try:
            year = int(year)
        except:
            year = 0
            
        self.conn.execute(query, {
            "paper_id": paper["paper_id"],
            "title": paper.get("title", "Untitled"),
            "year": year,
            "venue": paper.get("venue", ""),
            "abstract": paper.get("abstract", "")[:1000], # Truncate if too long (optional)
            "domain": paper.get("domain", ""),
            "novelty": paper.get("novelty", ""),
            "outcomes": paper.get("outcomes", ""),
            "source_file": paper.get("source_file", "")
        })

    def add_author_rel(self, faculty_name: str, paper_id: str):
        """Add Authored relationship."""
        # Ensure nodes exist first? specific ordering is better using MERGE
        query = """
        MATCH (f:Faculty {name: $faculty_name}), (p:Paper {paper_id: $paper_id})
        MERGE (f)-[:Authored]->(p)
        """
        self.conn.execute(query, {"faculty_name": faculty_name, "paper_id": paper_id})

    def add_topic(self, topic_id: str, name: str, category: str):
        query = "MERGE (t:Topic {topic_id: $topic_id}) SET t.name = $name, t.category = $category"
        self.conn.execute(query, {"topic_id": topic_id, "name": name, "category": category})

    def add_works_on(self, faculty_name: str, topic_id: str, weight: float = 1.0):
        query = """
        MATCH (f:Faculty {name: $faculty_name}), (t:Topic {topic_id: $topic_id})
        MERGE (f)-[r:WorksOn]->(t)
        SET r.weight = $weight
        """
        self.conn.execute(query, {"faculty_name": faculty_name, "topic_id": topic_id, "weight": weight})

    def add_concept(self, concept_id: str, name: str, type: str):
         query = "MERGE (c:Concept {concept_id: $concept_id}) SET c.name = $name, c.type = $type"
         self.conn.execute(query, {"concept_id": concept_id, "name": name, "type": type})

    def add_mentions(self, paper_id: str, concept_id: str):
        query = """
        MATCH (p:Paper {paper_id: $paper_id}), (c:Concept {concept_id: $concept_id})
        MERGE (p)-[:Mentions]->(c)
        """
        self.conn.execute(query, {"paper_id": paper_id, "concept_id": concept_id})
    
    def add_related(self, src_id: str, dst_id: str, relation: str, weight: float):
        query = """
        MATCH (a:Concept {concept_id: $src}), (b:Concept {concept_id: $dst})
        MERGE (a)-[r:RelatedTo]->(b)
        SET r.relation = $relation, r.weight = $weight
        """
        self.conn.execute(query, {"src": src_id, "dst": dst_id, "relation": relation, "weight": weight})
    
    def add_collaboration(self, faculty_a: str, faculty_b: str, weight: int):
        query = """
        MATCH (a:Faculty {name: $name_a}), (b:Faculty {name: $name_b})
        MERGE (a)-[r:CollaboratesWith]->(b)
        SET r.weight = $weight
        """
        self.conn.execute(query, {"name_a": faculty_a, "name_b": faculty_b, "weight": weight})
