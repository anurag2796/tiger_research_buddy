import json
import re
import time
import base64
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..chatbot.ollama_client import OllamaClient
from ..chatbot.gemini_client import get_gemini_client
from ..utils.config import DATA_DIR, GEMINI_API_KEY
from ..crawlers.vision_crawler import VisionCrawler
import fitz  # PyMuPDF - used for page image extraction only

console = Console()

class DeepDistiller:
    """
    Cognitive PDF Processor.
    Uses LLMs to 'read' research papers and distill them into structured Research Cards.
    Now powered by Vision-First Ingestion (Marker-PDF).
    """

    def __init__(self, pdf_dir: Path = DATA_DIR / "pdfs"):
        self.pdf_dir = pdf_dir
        self.output_dir = DATA_DIR / "research_cards"
        self.output_dir.mkdir(exist_ok=True)
        
        self.llm_client = OllamaClient()
        # Initialize Vision Crawler
        self.vision_crawler = VisionCrawler()
        
        # VLM client for validation (if API key available)
        self.vlm_client = None
        if GEMINI_API_KEY:
            try:
                self.vlm_client = get_gemini_client()
                console.print("[green]VLM validation enabled (Gemini)[/]")
            except Exception as e:
                console.print(f"[yellow]VLM validation unavailable: {e}[/]")
        
        # Load faculty database for author pre-resolution
        self.faculty_db = self._load_faculty_db()
        
    def extract_text(self, pdf_path: Path) -> str:
        """Extract high-quality markdown from PDF using VisionCrawler."""
        try:
            # Use Marker-PDF to convert to Markdown
            return self.vision_crawler.convert_pdf(str(pdf_path))
        except Exception as e:
            console.print(f"[red]Error reading {pdf_path.name}: {e}[/]")
            return ""
    
    def _load_faculty_db(self) -> Dict[str, Dict]:
        """Load RIT faculty database for author resolution."""
        try:
            with open(DATA_DIR / "rit_data_v2.json") as f:
                data = json.load(f)
                faculty = data.get("faculty", [])
                # Build lookup by normalized name
                db = {}
                for fac in faculty:
                    name = fac.get("name", "")
                    if name:
                        # Store under lowercase for fuzzy matching
                        db[name.lower()] = fac
                return db
        except Exception as e:
            console.print(f"[yellow]Could not load faculty DB: {e}[/]")
            return {}
    
    def _extract_page_image(self, pdf_path: Path, page_num: int = 0) -> Optional[str]:
        """Extract a page as base64-encoded PNG for VLM validation."""
        try:
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                page_num = 0
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            doc.close()
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            console.print(f"[yellow]Could not extract page image: {e}[/]")
            return None
    
    def _validate_table_with_vlm(self, pdf_path: Path, extracted_markdown: str, table_text: str) -> Tuple[bool, str]:
        """Use VLM to validate extracted table against PDF page image.
        
        Returns:
            (is_valid, corrected_table_or_original)
        """
        if not self.vlm_client:
            return True, table_text  # Skip validation if VLM unavailable
        
        # Extract first page with table (assume table is early in paper)
        # In production, use page detection logic
        page_image = self._extract_page_image(pdf_path, page_num=0)
        if not page_image:
            return True, table_text
        
        try:
            # Import multimodal support
            import google.generativeai as genai
            from PIL import Image
            import io
            
            # Decode image
            img_bytes = base64.b64decode(page_image)
            image = Image.open(io.BytesIO(img_bytes))
            
            # Initialize VLM with vision model
            self.vlm_client.initialize()
            genai.configure(api_key=GEMINI_API_KEY)
            vision_model = genai.GenerativeModel('gemini-1.5-pro')
            
            prompt = f"""Compare the following extracted table (in Markdown) against the table visible in this PDF page image.

Extracted Table (Markdown):
{table_text}

Task:
1. Verify if the Markdown accurately represents the table data in the image.
2. If correct, respond with: VALID
3. If incorrect or garbled, respond with: INVALID | followed by the corrected Markdown table.

Response:"""
            
            response = vision_model.generate_content([prompt, image])
            result = response.text.strip()
            
            if result.startswith("VALID"):
                console.print("[green]  ✓ VLM Validation: Table accurate[/]")
                return True, table_text
            elif result.startswith("INVALID"):
                parts = result.split("|", 1)
                if len(parts) == 2:
                    corrected = parts[1].strip()
                    console.print("[yellow]  ⚠ VLM Validation: Table corrected[/]")
                    return False, corrected
                else:
                    return False, table_text
            else:
                return True, table_text
                
        except Exception as e:
            console.print(f"[yellow]VLM validation error: {e}[/]")
            return True, table_text
    
    def _resolve_authors(self, raw_authors: List[str]) -> List[Dict]:
        """Pre-resolve author names against faculty database.
        
        Returns:
            List of author dicts with 'name' and optionally 'faculty_id' if matched.
        """
        resolved = []
        for author in raw_authors:
            if not author or not isinstance(author, str):
                continue
            
            author_lower = author.lower().strip()
            
            # Try exact match
            if author_lower in self.faculty_db:
                fac = self.faculty_db[author_lower]
                resolved.append({
                    "name": author,
                    "faculty_id": fac.get("name"),
                    "affiliation": "RIT"
                })
            else:
                # Fuzzy match (simple last name check)
                # In production, use full EntityResolver
                last_name = author.split()[-1].lower() if " " in author else author_lower
                matched = False
                for fac_name, fac_data in self.faculty_db.items():
                    if fac_name.endswith(last_name):
                        resolved.append({
                            "name": author,
                            "faculty_id": fac_data.get("name"),
                            "affiliation": "RIT"
                        })
                        matched = True
                        break
                
                if not matched:
                    # External author
                    resolved.append({"name": author})
        
        return resolved

    def _load_taxonomy(self) -> Dict:
        """Load the arXiv taxonomy seed."""
        try:
            with open(DATA_DIR / "taxonomies/arxiv_cs_taxonomy.json") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]Could not load taxonomy: {e}[/]")
            return {}

    def classify_domain(self, text: str) -> str:
        """Classify the paper text into a top-level domain."""
        taxonomy = self._load_taxonomy()
        domains = taxonomy.get("domains", {})
        
        prompt = f"""
        Analyze the following research abstract/intro and classify it into ONE of these domains:
        
        {json.dumps(domains, indent=2)}
        
        Input Text:
        {text[:2000]}
        
        Return ONLY the key (e.g. "cs.AI") or "Other".
        """
        
        try:
            response = self.llm_client.generate(prompt, system_prompt="You are a librarian.").strip()
            # Clean up response to get just the key
            for key in domains:
                if key in response:
                    return key
            return "Other"
        except Exception:
            return "Other"

    def repair_json(self, json_str: str) -> Optional[Dict]:
        """Attempt to repair common LLM JSON errors."""
        try:
            # 1. Try standard load first
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
        try:
            # 2. Fix unescaped newlines inside strings
            fixed_str = json_str.replace('\n', ' ')
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            pass
            
        try:
            # 3. Last resort: dirty regex to remove trailing commas
            fixed_str = re.sub(r",\s*([\]}])", r"\1", json_str)
            return json.loads(fixed_str)
        except Exception:
            return None

    def distill(self, text: str, filename: str, domain: str = "", pdf_path: Optional[Path] = None) -> Optional[Dict]:
        """Generate a Research Card using Qwen."""
        
        # Schema for the LLM to fill
        # TigerCard 2.0 Schema
        schema = {
            "card_id": "paper_unique_id",
            "bibliographic_data": {
                "title": "Paper Title",
                "authors": ["List", "of", "Authors"],
                "year": 2024,
                "venue": "Venue Name",
                "primary_domain": domain or "Domain",
                "sub_domain": "Sub-domain"
            },
            "core_content": {
                "novelty_claim": "One sentence summary of what is new.",
                "key_methodology": "Brief description of the method.",
                "limitations": "Known constraints or weaknesses.",
                "outcomes": ["Quantitative Result 1", "Qualitative Benefit 2"]
            },
            "knowledge_graph": {
                 "nodes": [
                     {"id": "node_id", "label": "Label", "type": "Concept/Theorem/Method/Metric"}
                 ],
                 "edges": [
                     {"source": "node_id_a", "target": "node_id_b", "relation": "EXTENDS/USES/PART_OF"}
                 ]
            }
        }

        # Truncate to safe limit (30k chars ~ 7.5k tokens)
        safe_text = text[:30000]

        domain_hint = ""
        if domain and domain != "Other":
            domain_hint = f"IMPORTANT: This is a '{domain}' paper. Extract entities (Theorems, Methods, Concepts) SPECIFIC to {domain}."

        prompt = f"""
        You are a Senior Research Scientist.
        Distill the following research paper (provided in Markdown) into a structured JSON 'TigerCard 2.0'.
        
        {domain_hint}
        
        CRITICAL: Output MUST be valid JSON (no markdown fences) matching this EXACT schema:
        
        Target JSON Schema:
        {json.dumps(schema, indent=2)}
        
        ### ONE-SHOT EXAMPLE ###
        Input:
        # Deep Residual Learning for Image Recognition
        ## Abstract
        We present a residual learning framework...
        
        Output:
        {{
          "card_id": "paper_deep_residual_learning_for_image_recognition",
          "bibliographic_data": {{
            "title": "Deep Residual Learning for Image Recognition",
            "authors": ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            "year": 2016,
            "venue": "CVPR",
            "primary_domain": "cs.CV"
          }},
          "core_content": {{
            "novelty_claim": "Introduces residual learning framework to ease training of deep networks.",
            "key_methodology": "Reformulate layers as learning residual functions with reference to layer inputs.",
            "limitations": "Deeper networks are harder to train without residual connections.",
            "outcomes": ["First place in ILSVRC 2015 classification task", "3.57% error on ImageNet test set"]
          }},
          "knowledge_graph": {{
            "nodes": [
              {{"id": "residual_learning", "label": "Residual Learning", "type": "Method"}},
              {{"id": "vanishing_gradient", "label": "Vanishing Gradient", "type": "Concept"}}
            ],
            "edges": [
              {{"source": "residual_learning", "target": "vanishing_gradient", "relation": "SOLVES"}}
            ]
          }}
        }}
        ### END EXAMPLE ###
        
        Ontology Rules:
        - **Concept**: Core idea (e.g. "Attention").
        - **Theorem**: Named rule (e.g. "Bayes Theorem").
        - **Method**: Technique (e.g. "Dropout").
        - **Metric**: Benchmark (e.g. "Accuracy").
        
        --- PAPER MARKDOWN ---
        {safe_text}
        
        --- END OF PAPER ---
        Response (JSON Only):
        """

        # console.print(f"[dim]Prompt:\n{prompt[:500]}...[/]")
        
        try:
            self.llm_client.initialize()
            # 2. Distill with LLM
            response = self.llm_client.generate(
                prompt, 
                system_prompt="You are a Scientific Knowledge Distiller.",
                format='json'
            )
            
            console.print(f"[bold red]RAW LLM RESPONSE:[/]\n{response[:1000]}")
            
            # Clean JSON (Ollama might still include markdown fences even in JSON mode)
            clean_text = response.replace("```json", "").replace("```", "").strip()
            
            # Extract JSON object if surrounded by text
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
            
            card = None
            try:
                card = json.loads(clean_text)
            except json.JSONDecodeError:
                # Attempt repair
                card = self.repair_json(clean_text)
                
            if not card:
                # Save failure for debug
                debug_path = DATA_DIR / "debug_failures" / f"failed_{filename}.txt"
                with open(debug_path, "w") as f:
                    f.write(response)
                console.print(f"[yellow]JSON Syntax Error. Saved to {debug_path}[/]")
                return None
            
            # Normalize Schema (Robustness Adapter)
            card = self._normalize_card(card)
            
            if card:
                card["source_file"] = filename
                
                # Post-process: Author resolution
                if "bibliographic_data" in card and "authors" in card["bibliographic_data"]:
                    raw_authors = card["bibliographic_data"]["authors"]
                    if isinstance(raw_authors, list):
                        resolved_authors = self._resolve_authors(raw_authors)
                        card["bibliographic_data"]["authors"] = resolved_authors
                
                # Post-process: VLM table validation (if PDF path provided)
                if pdf_path and self.vlm_client:
                    markdown_text = card.get("core_content", {}).get("full_text_markdown", "")
                    if "|" in markdown_text:  # Heuristic: contains table
                        console.print("  [cyan]Detected table, running VLM validation...[/]")
                        # Extract table portion (naive: find markdown table)
                        table_match = re.search(r"(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n)+)", markdown_text, re.MULTILINE)
                        if table_match:
                            table_text = table_match.group(1)
                            is_valid, corrected = self._validate_table_with_vlm(pdf_path, markdown_text, table_text)
                            if not is_valid:
                                # Replace table in markdown
                                markdown_text = markdown_text.replace(table_text, corrected)
                                card["core_content"]["full_text_markdown"] = markdown_text
                
                return card

        except Exception as e:
            console.print(f"[red]Distillation error for {filename}: {e}[/]")
            return None

    def _normalize_card(self, card: Dict) -> Dict:
        """Normalize semantic fallback fields into TigerCard 2.0 schema."""
        # STRICT ENFORCEMENT: Ensure all required fields exist
        required_fields = ["card_id", "bibliographic_data", "core_content", "knowledge_graph"]
        
        # If it already has the main keys, validate structure
        if all(field in card for field in required_fields):
            # Ensure knowledge_graph has nodes and edges
            if "nodes" not in card["knowledge_graph"]:
                card["knowledge_graph"]["nodes"] = []
            if "edges" not in card["knowledge_graph"]:
                card["knowledge_graph"]["edges"] = []
            return card
            
        console.print("[yellow]⚠️  LLM output deviated from schema. Normalizing...[/]")
        
        # 1. Build Base Structure
        new_card = {
            "card_id": card.get("card_id", "auto_generated"),
            "bibliographic_data": card.get("bibliographic_data", {}),
            "core_content": card.get("core_content", {}),
            "knowledge_graph": card.get("knowledge_graph", {"nodes": [], "edges": []})
        }
        
        # 2. Map Bibliographic Data
        if "title" in card and "title" not in new_card["bibliographic_data"]:
             new_card["bibliographic_data"]["title"] = card["title"]
        if "title" in card and isinstance(card["title"], str): # handle lowercase
             new_card["bibliographic_data"]["title"] = card["title"]
        if "Title" in card:
             new_card["bibliographic_data"]["title"] = card["Title"]
             
        if "author" in card:
             new_card["bibliographic_data"]["authors"] = card["author"] if isinstance(card["author"], list) else [card["author"]]
        if "Author" in card:
             new_card["bibliographic_data"]["authors"] = card["Author"] if isinstance(card["Author"], list) else [card["Author"]]

        # 3. Map Core Content
        if "summary" in card:
            new_card["core_content"]["novelty_claim"] = card["summary"]
        if "Summary" in card:
            new_card["core_content"]["novelty_claim"] = card["Summary"]
            
        # 4. Map Concepts to Knowledge Graph
        # Handle 'concepts', 'Key_Concepts', 'keywords'
        raw_concepts = []
        if "concepts" in card: raw_concepts.extend(card["concepts"])
        if "Key_Concepts" in card: raw_concepts.extend([c.get("Concept") for c in card["Key_Concepts"] if isinstance(c, dict) and "Concept" in c])
        if "keywords" in card: raw_concepts.extend(card["keywords"])
        
        # Deduplicate and add
        seen = set()
        for concept in raw_concepts:
            if isinstance(concept, str) and concept.lower() not in seen:
                seen.add(concept.lower())
                node_id = concept.lower().replace(" ", "_")
                new_card["knowledge_graph"]["nodes"].append({
                    "id": node_id,
                    "label": concept,
                    "type": "Concept"
                })
                
        return new_card

    def process_all(self):
        """Process all PDFs in the directory."""
        pdfs = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdfs:
            console.print(f"[yellow]No PDFs found in {self.pdf_dir}[/]")
            return

        console.print(f"[bold blue]⚗️ Starting Deep Distillation on {len(pdfs)} papers...[/]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console
        ) as progress:
            task = progress.add_task("Distilling...", total=len(pdfs))
            
            for pdf_path in pdfs:
                # Check if already processed
                output_path = self.output_dir / f"{pdf_path.stem}_card.json"
                if output_path.exists():
                    progress.advance(task)
                    continue
                
                # 1. Read
                text = self.extract_text(pdf_path)
                if len(text) < 100:
                    progress.advance(task)
                    continue
                
                # 1.5 Classify
                progress.update(task, description=f"Classifying {pdf_path.name[:20]}...")
                domain = self.classify_domain(text)
                console.print(f"   [dim]Domain: {domain}[/]")

                # 2. Distill (pass PDF path for VLM validation)
                progress.update(task, description=f"Distilling {pdf_path.name[:20]}...")
                card = self.distill(text, pdf_path.name, domain=domain, pdf_path=pdf_path)
                
                # 3. Graph Extraction (Deprecated - Now in TigerCard 2.0)
                # card["knowledge_graph"] is populated by distill()
                
                # 4. Save
                if card:
                    with open(output_path, "w") as f:
                        json.dump(card, f, indent=2)
                
                progress.advance(task)

        console.print(f"[green]✅ Distillation complete. Cards saved to {self.output_dir}[/]")
