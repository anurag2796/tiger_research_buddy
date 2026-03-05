import json
import re
import time
import base64
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..chatbot.ollama_client import OllamaClient
from ..chatbot.gemini_client import get_gemini_client
from ..utils.config import DATA_DIR, GEMINI_API_KEY, LLMConfig
from ..utils.db_logger import setup_db_logging, log_timing, PerformanceTimer as Timer
from ..crawlers.vision_crawler import VisionCrawler
from .vlm_target_extractor import VLMTargetExtractor
import fitz  # PyMuPDF - used for page image extraction only

logger = setup_db_logging("DeepDistiller")

console = Console()

class DeepDistiller:
    """
    Cognitive PDF Processor.
    Uses LLMs to 'read' research papers and distill them into structured Research Cards.
    Now powered by Vision-First Ingestion (Marker-PDF).
    """

    def __init__(self, pdf_dir: Path = None, faculty_db_path: Path = None):
        # Allow full config-aware overrides; fall back to global defaults
        self.pdf_dir = pdf_dir if pdf_dir is not None else DATA_DIR / "pdfs"
        self.output_dir = DATA_DIR / "research_cards"
        self.output_dir.mkdir(exist_ok=True)
        self._faculty_db_path = faculty_db_path  # Override for faculty JSON
        
        self.llm_client = OllamaClient(model=LLMConfig.PIPELINE_MODEL)
        # Initialize Vision Crawler with accelerated engine
        self.vision_crawler = VisionCrawler(engine="apple_fast")
        
        # VLM client for validation (if API key available)
        self.vlm_client = None
        if GEMINI_API_KEY:
            try:
                self.vlm_client = get_gemini_client()
                console.print("[green]VLM validation enabled (Gemini)[/]")
            except Exception as e:
                console.print(f"[yellow]VLM validation unavailable: {e}[/]")
        
        # VLM Target Extractor for bounding-box-isolated tables/figures.
        # Uses Ollama multimodal (local); swap backend="remote" for GPU server.
        self.target_extractor = VLMTargetExtractor(backend="local", model="llava")
        
        # Load faculty database for author pre-resolution
        self.faculty_db = self._load_faculty_db()
        
    @log_timing("Extract Text from PDF")
    async def extract_text_async(self, pdf_path: Path) -> str:
        """Extract high-quality markdown from PDF using VisionCrawler (Async Wrapper).

        Vision type guard: VisionCrawler.convert() is expected to return a dict
        with a 'content' key, but on certain failure paths (e.g. a backend that
        raises internally and returns a str error) it can return a bare string.
        Calling .get('content') on a str raises:
            'str' object has no attribute 'get_image'
        We guard against this explicitly and log the anomaly so it's traceable.
        """
        import asyncio
        try:
            # Run blocking extraction in thread pool
            with Timer(f"Extracting text from {pdf_path.name}", use_rich=False):
                result = await asyncio.to_thread(self.vision_crawler.convert, str(pdf_path))

            # Type guard: result must be a dict
            if isinstance(result, dict):
                return result.get("content", "")
            elif isinstance(result, str):
                # Backend returned a raw string (likely an error message or raw text)
                logger.warning(
                    f"Vision extraction returned str instead of dict for {pdf_path.name}. "
                    f"Using raw string directly. Preview: {result[:80]!r}"
                )
                return result
            else:
                logger.error(
                    f"Vision extraction returned unexpected type {type(result).__name__} "
                    f"for {pdf_path.name}. Skipping."
                )
                return ""
        except Exception as e:
            logger.error(f"Error reading {pdf_path.name}: {e}")
            console.print(f"[red]Error reading {pdf_path.name}: {e}[/]")
            return ""

    async def _extract_with_layout(self, pdf_path: Path) -> Tuple[str, List[Dict]]:
        """Extract text AND layout blocks (Table/Figure crops) from a PDF.

        Returns (content_text, layout_blocks) where layout_blocks is a list
        of dicts with 'type', 'bbox', 'page', 'cropped_image' keys.  If the
        engine doesn't produce layout blocks (e.g. Marker) the list is empty.
        """
        try:
            result = await asyncio.to_thread(
                self.vision_crawler.convert, str(pdf_path)
            )
        except Exception as e:
            logger.error(f"Error reading {pdf_path.name}: {e}")
            return "", []

        if isinstance(result, dict):
            text = result.get("content", "")
            # Collect layout_blocks across all pages
            layout_blocks = []
            for page in result.get("pages", []):
                layout_blocks.extend(page.get("layout_blocks", []))
            return text, layout_blocks
        elif isinstance(result, str):
            return result, []
        else:
            return "", []

    @log_timing("Extract Text from PDF")
    def extract_text(self, pdf_path: Path) -> str:
        """Extract high-quality markdown from PDF using VisionCrawler."""
        # Non-async version for backward compatibility if needed
        import asyncio
        return asyncio.run(self.extract_text_async(pdf_path))
    
    def _load_faculty_db(self) -> Dict[str, Dict]:
        """Load RIT faculty database for author resolution."""
        # Use the override path if provided (e.g. restricted mode JSON)
        candidate_paths = []
        if self._faculty_db_path and self._faculty_db_path.exists():
            candidate_paths.append(self._faculty_db_path)
        # Fallback chain: v2 → restricted
        candidate_paths += [
            DATA_DIR / "rit_data_v2.json",
            DATA_DIR / "restricted" / "rit_data_restricted.json",
        ]
        for path in candidate_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    faculty = data.get("faculty", [])
                    db = {fac["name"].lower(): fac for fac in faculty if fac.get("name")}
                    console.print(f"[dim]Faculty DB loaded: {len(db)} entries from {path.name}[/]")
                    return db
                except Exception as e:
                    logger.warning(f"Could not load faculty DB from {path}: {e}")
        console.print("[yellow]No faculty DB found — author resolution disabled.[/]")
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

    async def classify_domain_async(self, text: str) -> str:
        """Classify the paper text into a top-level domain (Async)."""
        taxonomy = await asyncio.to_thread(self._load_taxonomy)
        domains = taxonomy.get("domains", {})
        
        prompt = f"""
        Analyze the following research abstract/intro and classify it into ONE of these domains:
        
        {json.dumps(domains, indent=2)}
        
        Input Text:
        {text[:2000]}
        
        Return ONLY the key (e.g. "cs.AI") or "Other".
        """
        
        try:
            with Timer(f"Classifying domain for items", use_rich=False):
                response = await self.llm_client.generate_async(prompt, system_prompt="You are a librarian.")
                response = response.strip()
            # Clean up response to get just the key
            for key in domains:
                if key in response:
                    return key
            return "Other"
        except Exception:
            return "Other"

    def classify_domain(self, text: str) -> str:
        import asyncio
        return asyncio.run(self.classify_domain_async(text))

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

    def _extract_visual_elements(
        self, layout_blocks: List[Dict]
    ) -> List[Dict]:
        """Run VLM target prompting on each cropped Table/Figure region.

        Returns a list of dicts suitable for the TigerCard 2.0 schema:
            {"type": "Table"|"Figure", "page": int, "bbox": list, "markdown": str}
        """
        elements = []
        for block in layout_blocks:
            cropped = block.get("cropped_image")
            if cropped is None:
                continue

            element_type = block.get("type", "Figure")
            try:
                md = self.target_extractor.extract(cropped, element_type)
            except Exception as e:
                logger.warning(
                    f"VLM target extraction failed for {element_type} "
                    f"on page {block.get('page')}: {e}"
                )
                md = ""

            if md.strip():
                elements.append({
                    "type": element_type,
                    "page": block.get("page", 0),
                    "bbox": block.get("bbox", []),
                    "markdown": md,
                })
                console.print(
                    f"[green]  ✓ Target-extracted {element_type} on page "
                    f"{block.get('page', '?')} ({len(md)} chars)[/]"
                )

        return elements

    @log_timing("Distill Paper")
    async def distill_async(
        self,
        text: str,
        filename: str,
        domain: str = "",
        pdf_path: Optional[Path] = None,
        metadata: Dict = None,
        layout_blocks: Optional[List[Dict]] = None,
    ) -> Optional[Dict]:
        """Generate a Research Card using Qwen (Async).

        Parameters
        ----------
        layout_blocks : list[dict], optional
            Cropped Table/Figure images from Surya layout detection.
            When provided, each block is sent through VLM target prompting
            and the extracted Markdown is appended to the card.
        """
        import asyncio
        
        # Schema definition (same as before)
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

        # 1. Early-Exit Filter: Don't burn LLM compute on garbage OCR
        if not text or len(text.strip()) < 200:
            console.print(f"[yellow]Skipping distillation for {filename}: Text too short ({len(text)} chars)[/]")
            return None
            
        # 2. Context Truncation: Hard-limit to ~15k characters (~3k tokens)
        # This focuses the LLM on Abstract/Intro/Methods and prevents catastrophic
        # JSON truncation errors that occur when the model hits max_tokens mid-generation.
        safe_text = text[:15000]

        # ── VLM Target Prompting on cropped visual elements ──────────────
        visual_elements: List[Dict] = []
        if layout_blocks:
            console.print(
                f"[cyan]  🔬 Running VLM target prompting on "
                f"{len(layout_blocks)} layout block(s)...[/]"
            )
            visual_elements = await asyncio.to_thread(
                self._extract_visual_elements, layout_blocks
            )

            # Inject extracted table/figure markdown into the LLM context
            # so the distiller can reference accurate data when building the card.
            if visual_elements:
                ve_section = "\n\n--- EXTRACTED VISUAL ELEMENTS ---\n"
                for ve in visual_elements:
                    ve_section += (
                        f"\n### {ve['type']} (Page {ve['page']})\n"
                        f"{ve['markdown']}\n"
                    )
                ve_section += "\n--- END VISUAL ELEMENTS ---\n"
                safe_text += ve_section

        domain_hint = ""
        if domain and domain != "Other":
            domain_hint = f"IMPORTANT: This paper belongs to the '{domain}' domain. Extract entities (Theorems, Methods, Concepts) SPECIFIC to {domain}."
            
        # 3. Load Schema and Extraction Rules
        from ..utils.config import DATA_DIR
        schema_path = DATA_DIR.parent / "data" / "prompts" / "distiller_schema.md"
        try:
            with open(schema_path) as f:
                schema_rules = f.read()
        except FileNotFoundError:
            schema_rules = "You are a Research Assistant. Extract paper data into valid JSON."

        prompt = f"""
        {schema_rules}
        
        {domain_hint}
        
        --- PAPER MARKDOWN ---
        {safe_text}
        
        --- END OF PAPER ---
        Response (JSON Only):
        """

        try:
            self.llm_client.initialize()
            # 2. Distill with Async LLM
            with Timer(f"Distilling {filename}", use_rich=False):
                response = await self.llm_client.generate_async(
                    prompt, 
                    system_prompt="You are a Scientific Knowledge Distiller.",
                    format='json',
                    options=LLMConfig.DEFAULT_OPTIONS
                )
            
            # Clean JSON
            clean_text = response.replace("```json", "").replace("```", "").strip()
            
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
            
            card = None
            try:
                card = json.loads(clean_text)
            except json.JSONDecodeError:
                card = self.repair_json(clean_text)
                
            if not card:
                debug_path = DATA_DIR / "debug_failures" / f"failed_{filename}.txt"
                debug_path.parent.mkdir(exist_ok=True)
                with open(debug_path, "w") as f:
                    f.write(response)
                console.print(f"[yellow]JSON Syntax Error. Saved to {debug_path}[/]")
                return None
            
            # Normalize
            card = self._normalize_card(card)
            
            if card:
                card["source_file"] = filename
                
                # MERGE METADATA (Authoritative Override)
                if metadata:
                    bib = card.setdefault("bibliographic_data", {})
                    # Use metadata authors if available and valid
                    if metadata.get("authors") and isinstance(metadata["authors"], list) and len(metadata["authors"]) > 0:
                         bib["authors"] = metadata["authors"]
                    
                    if metadata.get("title"):
                        bib["title"] = metadata["title"]
                        
                    if metadata.get("year"):
                        bib["year"] = metadata["year"]
                        
                    if metadata.get("venue"):
                         bib["venue"] = metadata["venue"]
                
                # Resolve Authors (Faculty Matching)
                if "bibliographic_data" in card and "authors" in card["bibliographic_data"]:
                    raw_authors = card["bibliographic_data"]["authors"]
                    if isinstance(raw_authors, list):
                        resolved_authors = self._resolve_authors(raw_authors)
                        card["bibliographic_data"]["authors"] = resolved_authors
                
                if pdf_path and self.vlm_client:
                    markdown_text = card.get("core_content", {}).get("full_text_markdown", "")
                    if "|" in markdown_text:
                        # VLM call 
                        table_match = re.search(r"(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n)+)", markdown_text, re.MULTILINE)
                        if table_match:
                            table_text = table_match.group(1)
                            # Run VLM validation in thread
                            is_valid, corrected = await asyncio.to_thread(
                                self._validate_table_with_vlm, pdf_path, markdown_text, table_text
                            )
                            if not is_valid:
                                markdown_text = markdown_text.replace(table_text, corrected)
                                card["core_content"]["full_text_markdown"] = markdown_text
                
                # Attach VLM-extracted visual elements to TigerCard 2.0
                if visual_elements:
                    card.setdefault("core_content", {})["visual_elements"] = visual_elements
                
                return card

        except Exception as e:
            logger.error(f"Distillation error for {filename}: {e}")
            console.print(f"[red]Distillation error for {filename}: {e}[/]")
            return None

    @log_timing("Distill Paper")
    def distill(self, text: str, filename: str, domain: str = "", pdf_path: Optional[Path] = None) -> Optional[Dict]:
        import asyncio
        return asyncio.run(self.distill_async(text, filename, domain, pdf_path))

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

    async def process_one_pdf(self, pdf_path: Path, semaphore: asyncio.Semaphore, progress, task):
        """Process a single PDF with semaphore control."""
        async with semaphore:
            output_path = self.output_dir / f"{pdf_path.stem}_card.json"
            if output_path.exists():
                progress.advance(task)
                return

            # 1. Read with layout detection (Async)
            text, layout_blocks = await self._extract_with_layout(pdf_path)
            if len(text) < 100:
                progress.advance(task)
                return
            
            # 2. Load Metadata (if available)
            metadata = {}
            meta_path = DATA_DIR / "papers" / f"{pdf_path.stem}.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r") as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load metadata for {pdf_path.name}: {e}")

            # 3. Classify (Async)
            progress.update(task, description=f"Classifying {pdf_path.name[:20]}...")
            domain = await self.classify_domain_async(text)
            
            # 4. Distill with visual context (Async)
            progress.update(task, description=f"Distilling {pdf_path.name[:20]}...")
            card = await self.distill_async(
                text, pdf_path.name,
                domain=domain,
                pdf_path=pdf_path,
                metadata=metadata,
                layout_blocks=layout_blocks,
            )

            if card:
                with open(output_path, "w") as f:
                    json.dump(card, f, indent=2)
            
            progress.advance(task)

    async def process_all_async(self):
        """Process all PDFs in parallel."""
        import asyncio
        pdfs = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdfs:
            console.print(f"[yellow]No PDFs found in {self.pdf_dir}[/]")
            return

        console.print(f"[bold blue]⚗️ Starting Async Deep Distillation on {len(pdfs)} papers...[/]")
        
        # Limit concurrency to 3-5 to avoid OOM or LLM thrashing
        concurrency = 3
        semaphore = asyncio.Semaphore(concurrency)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} papers"),
            console=console
        ) as progress:
            task = progress.add_task("Distilling...", total=len(pdfs))
            
            tasks = [self.process_one_pdf(p, semaphore, progress, task) for p in pdfs]
            await asyncio.gather(*tasks)

        console.print(f"[green]✅ Distillation complete. Cards saved to {self.output_dir}[/]")

    def process_all(self):
        """Process all PDFs (Synchronous Wrapper)."""
        import asyncio
        asyncio.run(self.process_all_async())
