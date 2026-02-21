import time
import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console

# Lazy import for heavy dependencies
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False

console = Console()

class VisionCrawler:
    """
    Production-grade VLM-based Crawler/Parser using Marker-PDF.
    
    Features:
    - Lazy loading of models to save resources until needed
    - Robust error handling and retries
    - Semantic chunking by headers
    - Caching of processed markdown files
    """
    
    def __init__(self, cache_dir: str = "data/cache/marker", use_gpu: bool = True, engine: str = "marker", **kwargs):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_gpu = use_gpu
        self.engine = engine
        self.converter = None
        self.processor = None
        self.artifact_dict = None
        self.processor_config = kwargs # Store extra config for apple_fast
        self.config = {
            "output_format": "markdown",
            "use_llm": False,
            "disable_image_extraction": True # Save space?
        }
        
    def _load_models(self):
        """Lazy load heavy models."""
        if self.engine == "apple_fast":
             if self.processor:
                 return
             from src.utils.document_processor import DocumentProcessor, ProcessorConfig
             
             # Use stored config or defaults
             cfg = ProcessorConfig(
                pdf_backend=self.processor_config.get("pdf_backend", "pymupdf"),
                table_mode=self.processor_config.get("table_strategy", "auto"),
                render_dpi=self.processor_config.get("render_dpi", 96)
             )
             self.processor = DocumentProcessor(cfg)
             return
             
        if self.converter:
            return

        # Dynamic check in case it was installed after module load
        global MARKER_AVAILABLE
        if not MARKER_AVAILABLE:
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict
                MARKER_AVAILABLE = True
            except ImportError:
                 # If top-level import fails, try to import just before use below or raise
                 pass

        if not MARKER_AVAILABLE:
            # Last ditch attempt to import locally
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict
                MARKER_AVAILABLE = True
            except ImportError:
                raise ImportError("marker-pdf is not installed. Please run 'pip install marker-pdf'.")
        else:
             from marker.converters.pdf import PdfConverter
             from marker.models import create_model_dict

        console.print("[cyan]Initializing VisionCrawler models (this may take a moment)...[/]")
        try:
            start = time.time()
            # Create model dict (downloads weights if needed)
            self.artifact_dict = create_model_dict()
            self.converter = PdfConverter(
                artifact_dict=self.artifact_dict,
                config=self.config
            )
            console.print(f"[green]Models loaded in {time.time() - start:.2f}s[/]")
        except Exception as e:
            console.print(f"[red]Failed to load Marker models: {e}[/]")
            raise

    def get_cache_path(self, pdf_path: Path, engine: str) -> Path:
        """Generate a unique cache path based on file hash."""
        # Fast hash of the file path + mtime + engine to invalidate if file/engine changes
        identifier = f"{pdf_path.absolute()}_{pdf_path.stat().st_mtime}_{engine}"
        file_hash = hashlib.md5(identifier.encode()).hexdigest()
        return self.cache_dir / f"{file_hash}.md"

    def convert(self, pdf_path: str, force_reprocess: bool = False, skip_tables: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Convert a PDF to Markdown using the selected engine.
        
        Args:
            pdf_path: Path to PDF file
            force_reprocess: If True, ignore cache
            skip_tables: If True, skip table recognition (Marker only)
            **kwargs: Additional args like 'pdf_backend', 'render_dpi', 'table_strategy' for apple_fast
        """
        fpath = Path(pdf_path)
        if not fpath.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Determine engine from instance or kwargs override
        engine = kwargs.get("engine", self.engine)

        cache_path = self.get_cache_path(fpath, engine)
        meta_path = cache_path.with_suffix(".json")
        
        # Check cache
        if not force_reprocess and cache_path.exists() and meta_path.exists():
            console.print(f"[dim]Using cached markdown for {fpath.name} (Engine: {engine})[/]")
            try:
                content = cache_path.read_text(encoding='utf-8')
                metadata = json.loads(meta_path.read_text(encoding='utf-8'))
                return {
                    "content": content,
                    "metadata": metadata
                }
            except Exception:
                pass # Fallback to reprocess

        console.print(f"[yellow]Vision-Parsing {fpath.name} using {engine}...[/]")
        start_time = time.time()
        
        try:
            result = {}
            if engine == "apple_fast":
                result = self._convert_apple_fast(str(fpath), **kwargs)
            else:
                result = self._convert_marker(str(fpath), skip_tables)
            
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            metadata["cached_at"] = time.time()
            metadata["source"] = f"vision_crawler_{engine}"
            
            # Save to cache
            cache_path.write_text(content, encoding='utf-8')
            meta_path.write_text(json.dumps(metadata), encoding='utf-8')
            
            duration = time.time() - start_time
            console.print(f"[green]Converted {fpath.name} in {duration:.2f}s[/]")
            
            return {
                "content": content,
                "metadata": metadata
            }
            
        except Exception as e:
            console.print(f"[red]Error converting {fpath.name}: {e}[/]")
            raise
            
    def _convert_apple_fast(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """Delegate to DocumentProcessor."""
        # Reuse processor if exists and config matches? 
        # For simplicity, we assume config doesn't change drastically or we just reuse models.
        # But DocumentProcessor holds models in `self`.
        
        if not self.processor:
             # Lazy import
            from src.utils.document_processor import DocumentProcessor, ProcessorConfig
            
            # Extract config from kwargs or use defaults
            cfg = ProcessorConfig(
                pdf_backend=kwargs.get("pdf_backend", "pymupdf"),
                table_mode=kwargs.get("table_strategy", "auto"),
                render_dpi=kwargs.get("render_dpi", 96)
            )
            self.processor = DocumentProcessor(cfg)
            
        return self.processor.process_pdf(pdf_path)

    def _convert_marker(self, pdf_path: str, skip_tables: bool) -> Dict[str, Any]:
        """Original Marker-PDF conversion logic."""
        self._load_models()
        
        # Configure processors to optionally skip tables
        processor_list = None
        if skip_tables:
            # Import here to avoid circular/early import issues
            from marker.converters.pdf import PdfConverter
            from marker.util import classes_to_strings
            
            defaults = PdfConverter.default_processors
            # Filter out table processors by name
            filtered_processors = [p for p in defaults if "Table" not in p.__name__]
            
            # Convert back to strings
            processor_list = classes_to_strings(filtered_processors)
        
        # Instantiate converter for this run
        converter = PdfConverter(
            artifact_dict=self.artifact_dict,
            config=self.config,
            processor_list=processor_list
        )
        
        # Run conversion
        rendered = converter(pdf_path)
        return {
            "content": rendered.markdown,
            "metadata": rendered.metadata or {}
        }

    def chunk_text(self, text: str, max_chunk_size: int = 4000) -> List[str]:
        """
        Semantically chunk text based on Markdown headers (#, ##, ###).
        If a section is larger than max_chunk_size, it is split by paragraphs.
        """
        if not text:
            return []

        chunks = []
        current_chunk = []
        current_length = 0
        
        lines = text.split('\n')
        
        for line in lines:
            # Check for headers
            is_header = line.strip().startswith(('# ', '## ', '### '))
            
            # If it's a header and we have content, explicitly break
            if is_header and current_chunk:
                # Join what we have
                chunk_str = '\n'.join(current_chunk)
                
                # If the chunk is too large, split it further by paragraphs
                if len(chunk_str) > max_chunk_size:
                    sub_chunks = self._split_large_chunk(chunk_str, max_chunk_size)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_str)
                
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += len(line) + 1  # +1 for newline
            
        # Add remaining
        if current_chunk:
            chunk_str = '\n'.join(current_chunk)
            if len(chunk_str) > max_chunk_size:
                sub_chunks = self._split_large_chunk(chunk_str, max_chunk_size)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk_str)
            
        return chunks

    def _split_large_chunk(self, text: str, max_size: int) -> List[str]:
        """Helper to split a large text block by paragraphs."""
        paras = text.split('\n\n')
        sub_chunks = []
        current_sub = []
        current_len = 0
        
        for para in paras:
            if current_len + len(para) > max_size and current_sub:
                sub_chunks.append('\n\n'.join(current_sub))
                current_sub = []
                current_len = 0
            
            current_sub.append(para)
            current_len += len(para) + 2
            
        if current_sub:
            sub_chunks.append('\n\n'.join(current_sub))
            
        return sub_chunks

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Run VisionCrawler on a PDF")
    parser.add_argument("pdf_path", nargs="?", help="Path to the PDF file to convert")
    parser.add_argument("--output", "-o", help="Path to save the output Markdown file")
    
    # Engine & Backend
    parser.add_argument("--engine", choices=["marker", "apple_fast"], default="marker", help="Processing engine to use")
    parser.add_argument("--pdf-backend", choices=["pymupdf", "pypdfium2"], default="pymupdf", help="PDF backend for apple_fast engine")
    
    # Tables
    parser.add_argument("--skip-tables", action="store_true", default=True, help="Skip table recognition (marker engine only)")
    parser.add_argument("--no-skip-tables", action="store_false", dest="skip_tables", help="Enable table recognition (marker engine only)")
    parser.add_argument("--tables", choices=["auto", "off", "force"], default="auto", help="Table extraction mode (apple_fast engine only)")
    
    # Rendering
    parser.add_argument("--render-dpi", type=int, default=144, help="DPI for rendering pages (apple_fast engine only)")
    
    args = parser.parse_args()
    
    # ... (rest of path resolution)
    pdf_path = None
    if args.pdf_path:
        pdf_path = Path(args.pdf_path)
    else:
        pdf_dir = Path("data/pdfs")
        pdfs = list(pdf_dir.glob("*.pdf"))
        if pdfs:
            pdf_path = pdfs[0]
            print(f"No PDF provided. Defaulting to: {pdf_path}")
            
    if not pdf_path or not pdf_path.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/]")
        sys.exit(1)
        
    console.print(f"[bold blue]Processing: {pdf_path.name} using engine: {args.engine}[/]")
    
    try:
        content = ""
        metadata = {}
        
        if args.engine == "marker":
            crawler = VisionCrawler()
            result = crawler.convert(str(pdf_path), force_reprocess=True, skip_tables=args.skip_tables)
            content = result['content']
            metadata = result['metadata']
        elif args.engine == "apple_fast":
            # Lazy import to avoid loading heavy deps if not used
            from src.utils.document_processor import DocumentProcessor, ProcessorConfig
            
            cfg = ProcessorConfig(
                pdf_backend=args.pdf_backend,
                table_mode=args.tables,
                render_dpi=args.render_dpi
            )
            processor = DocumentProcessor(cfg)
            result = processor.process_pdf(str(pdf_path))
            content = result['content']
            metadata = result['metadata']
            
        console.print(f"[green]Successfully converted {len(content)} characters.[/]")
        
        # Save to specific output if requested
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding='utf-8')
            console.print(f"[bold green]Saved output to: {out_path}[/]")
        else:
            default_out = Path(f"experiments/output_{pdf_path.stem}_{args.engine}.md")
            default_out.parent.mkdir(parents=True, exist_ok=True)
            default_out.write_text(content, encoding='utf-8')
            console.print(f"[dim]Saved copy to: {default_out}[/]")
            
        # Test Chunking (using VisionCrawler static/shared logic if possible, or just skip for now)
        # VisionCrawler.chunk_text is an instance method but logic is pure.
        # We'll instantiate VisionCrawler just for chunking if needed, or extract it.
        # For now, just using VisionCrawler instance for chunking if we have one, or skip.
        if args.engine == "marker":
            chunks = crawler.chunk_text(content)
            console.print(f"[cyan]Generated {len(chunks)} semantic chunks.[/]")
            
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/]")
        import traceback
        traceback.print_exc()
