
import os
import io
import sys
import json
import time
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from abc import ABC, abstractmethod

from PIL import Image

# ---- Surya (OCR + layout) ----
try:
    from surya.layout import LayoutPredictor
    SURYA_AVAILABLE = True
except ImportError:
    SURYA_AVAILABLE = False

# ---- GMFT (tables) ----
try:
    from gmft.auto import AutoTableDetector, AutoTableFormatter
    GMFT_AVAILABLE = True
except ImportError:
    GMFT_AVAILABLE = False

# ---- Backend Adapters ----
class PDFAdapter(ABC):
    @abstractmethod
    def open(self, path: str):
        pass

    @abstractmethod
    def get_page_text(self, page_index: int) -> str:
        pass
    
    @abstractmethod
    def render_page(self, page_index: int, dpi: int) -> Image.Image:
        pass
    
    @abstractmethod
    def get_page_count(self) -> int:
        pass
    
    @abstractmethod
    def close(self):
        pass

class FitzAdapter(PDFAdapter):
    def __init__(self):
        try:
            import fitz
            self.fitz = fitz
        except ImportError:
            raise ImportError("pymupdf not installed. Use pip install pymupdf")
        self.doc = None

    def open(self, path: str):
        self.doc = self.fitz.open(path)

    def get_page_text(self, page_index: int) -> str:
        return self.doc.load_page(page_index).get_text("text")

    def render_page(self, page_index: int, dpi: int) -> Image.Image:
        page = self.doc.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")

    def get_page_count(self) -> int:
        return self.doc.page_count

    def close(self):
        if self.doc:
            self.doc.close()

class PdfiumAdapter(PDFAdapter):
    def __init__(self):
        try:
            import pypdfium2 as pdfium
            self.pdfium = pdfium
        except ImportError:
            raise ImportError("pypdfium2 not installed. Use pip install pypdfium2")
        self.doc = None

    def open(self, path: str):
        self.doc = self.pdfium.PdfDocument(path)

    def get_page_text(self, page_index: int) -> str:
        page = self.doc.get_page(page_index)
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        return text

    def render_page(self, page_index: int, dpi: int) -> Image.Image:
        page = self.doc.get_page(page_index)
        # pypdfium2 scale = dpi / 72
        scale = dpi / 72.0
        bitmap = page.render(scale=scale, rotation=0)
        pil_image = bitmap.to_pil()
        return pil_image.convert("RGB")

    def get_page_count(self) -> int:
        return len(self.doc)

    def close(self):
        if self.doc:
            self.doc.close()

@dataclass
class ProcessorConfig:
    # Text gating
    min_digital_chars: int = 100
    min_digital_words: int = 20 # heuristic for "meaningful" content
    min_unique_ratio: float = 0.1 # reject "aaaaa..." junk
    
    # OCR rendering
    render_dpi: int = 144
    max_render_px: int = 2048
    
    # Table gating
    table_mode: str = "auto" # "auto", "off", "force"
    table_backend: str = "gmft" # "gmft"
    
    # Backend
    pdf_backend: str = "pymupdf" # "pymupdf" or "pypdfium2"
    
    # Caching
    cache_dir: str = ".cache/docproc"
    engine_version: str = "1.0.0"
    
    # Model Versions (for cache key)
    model_versions: Dict[str, str] = field(default_factory=dict)

class DiskCache:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        p = self._path(key)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        p = self._path(key)
        # Atomic write
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)
        os.replace(tmp, p)

def stable_file_hash(path: str, block_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(block_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def downscale_pil(im: Image.Image, max_px: int) -> Image.Image:
    w, h = im.size
    scale = min(max_px / max(w, h), 1.0)
    if scale >= 1.0:
        return im
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return im.resize((new_w, new_h))

class DocumentProcessor:
    """
    Hardware-Aware PDF Processing Pipeline.

    Supports macOS (MPS), Jetson (CUDA), and CPU-only environments.
    Layout detection (Surya) is disabled on edge devices with < 16 GB
    unified memory to prevent OOM during batch distillation.
    """
    def __init__(self, cfg: ProcessorConfig):
        self.cfg = cfg
        self.cache = DiskCache(cfg.cache_dir)
        
        # Load models lazily or on init? Init is safer for "fast by default" claims 
        # but expensive if not used. Given this class is called when engine=apple_fast,
        # we assume usage.
        
        self.rec_model = None
        self.rec_processor = None
        self.det_model = None
        self.det_processor = None
        self.layout_model = None
        self.layout_processor = None

        # Surya layout predictor for bounding-box detection of tables/figures.
        # Disabled on edge devices where VRAM is shared with the LLM (Jetson Orin).
        self.layout_predictor = None
        if SURYA_AVAILABLE:
            # Guard: skip Surya on Jetson / low-memory platforms to avoid OOM.
            # The Surya LayoutPredictor loads a ~400MB ViT model onto GPU.
            _skip_layout = False
            try:
                from ..utils.hardware import HW_PROFILE
                if HW_PROFILE.platform.startswith("linux") and HW_PROFILE.chat_concurrency <= 1:
                    _skip_layout = True
                    logging.getLogger(__name__).info(
                        "Surya layout detection disabled on edge device to conserve VRAM"
                    )
            except ImportError:
                pass  # hardware module not available; proceed with Surya

            if not _skip_layout:
                try:
                    self.layout_predictor = LayoutPredictor()
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Surya initialization failed: {e}")
                    pass  # Graceful fallback — layout detection disabled

        if GMFT_AVAILABLE and self.cfg.table_mode != "off":
            try:
                self.gmft_detector = AutoTableDetector()
                self.gmft_formatter = AutoTableFormatter()
            except Exception as e:
                logging.getLogger(__name__).warning(f"GMFT initialization failed: {e}")
                self.gmft_detector = None
                self.gmft_formatter = None
        else:
            self.gmft_detector = None
            self.gmft_formatter = None
            
        self._doc_tables_cache = {}
        self.doc_langs = ["en"] # Default to English

    def process_pdf(self, pdf_path: str, max_pages: int = 0) -> Dict[str, Any]:
        """Convert a PDF to structured text and table output.

        Recursion guard: PyMuPDF can hit Python's default recursion limit on
        PDFs with circular or deeply-nested cross-reference trees. We raise
        the limit locally for this call and catch per-page RecursionErrors so
        that a single bad page doesn't discard the whole document.

        Args:
            pdf_path: Path to the PDF file.
            max_pages: Maximum number of pages to process.  0 = no limit.
        """
        # Hash including file, config, versions
        file_hash = stable_file_hash(pdf_path)
        config_hash = hashlib.md5(json.dumps(self.cfg.__dict__, sort_keys=True, default=str).encode()).hexdigest()
        cache_key = f"{file_hash}_{self.cfg.engine_version}_{config_hash}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        t0 = time.time()

        # Select Backend
        if self.cfg.pdf_backend == "pypdfium2":
            adapter = PdfiumAdapter()
        else:
            adapter = FitzAdapter()

        adapter.open(pdf_path)

        pages_out = []
        # Raise recursion limit locally for this document only; restore after.
        _prev_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(_prev_limit, 5000))
        try:
            total_pages = adapter.get_page_count()
            pages_to_process = min(total_pages, max_pages) if max_pages > 0 else total_pages
            if pages_to_process < total_pages:
                logging.getLogger(__name__).info(
                    f"Processing {pages_to_process}/{total_pages} pages (max_pages={max_pages})")
            for i in range(pages_to_process):
                try:
                    page_out = self._process_page(adapter, i, pdf_path)
                except RecursionError:
                    # Malformed PDF with circular object references — skip this
                    # page but keep processing the rest of the document.
                    page_out = {
                        "page": i,
                        "text": "",
                        "text_source": "error",
                        "tables": []
                    }
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Error processing page {i}: {e}")
                    page_out = {
                        "page": i,
                        "text": "",
                        "text_source": "error_catchall",
                        "tables": []
                    }
                pages_out.append(page_out)
        finally:
            sys.setrecursionlimit(_prev_limit)
            adapter.close()

        out = {
            "pdf_path": pdf_path,
            "doc_pages": len(pages_out),
            "elapsed_s": round(time.time() - t0, 3),
            "pages": pages_out,
            "metadata": {
                "languages": ["en"],
                "page_count": len(pages_out),
                "ocr_stats": {}
            },
            # Construct a "marker-compatible" content string (skip error pages)
            "content": "\n\n".join([p["text"] for p in pages_out if p["text"]])
        }

        self.cache.set(cache_key, out)
        return out

    def _process_page(self, adapter: PDFAdapter, page_idx: int, pdf_path: str) -> Dict[str, Any]:
        raw_text = adapter.get_page_text(page_idx) or ""
        text_source = "digital"
        final_text = raw_text
        
        # 1. Digital Text Gate
        stripped = raw_text.strip()
        is_digital = False
        if len(stripped) >= self.cfg.min_digital_chars:
            words = len(stripped.split())
            unique_chars = len(set(stripped))
            if words >= self.cfg.min_digital_words and (unique_chars / len(stripped)) >= self.cfg.min_unique_ratio:
                is_digital = True
        
        pil_img = None 
        
        # 2. OCR Fallback
        if not is_digital:
            text_source = "ocr"
            pil_img = adapter.render_page(page_idx, self.cfg.render_dpi)
            pil_img_small = downscale_pil(pil_img, self.cfg.max_render_px)
            
            # Fallback: Try Tesseract if available
            try:
                import pytesseract
                final_text = pytesseract.image_to_string(pil_img)
            except ImportError:
                # No Tesseract -> Return raw text (better than placeholder garbage)
                final_text = raw_text or ""
            except Exception:
                final_text = raw_text or ""

        # 3. Table Gate (legacy GMFT path)
        tables = []
        run_tables = False
        if self.cfg.table_mode != "off":
            if self.cfg.table_mode == "force":
                run_tables = True
            elif self.cfg.table_mode == "auto":
                heuristic_pass = self._heuristic_table_check(final_text)
                if heuristic_pass:
                    run_tables = True

        if run_tables:
            tables = self._extract_tables_gmft(pdf_path, page_idx)

        # 4. Surya Layout Detection — isolate Table/Figure bounding boxes
        # Returns cropped PIL images for downstream VLM target prompting.
        layout_blocks = []
        if self.layout_predictor is not None:
            # Render page image if we haven't already (digital pages skip OCR render)
            if pil_img is None:
                pil_img = adapter.render_page(page_idx, self.cfg.render_dpi)

            # Guard: skip layout prediction for very large page images.
            # Surya's native backend can SIGTRAP on dense/oversized images.
            w, h = pil_img.size
            if w * h <= 10_000_000:  # 10 megapixels
                layout_blocks = self._detect_layout_blocks(pil_img, page_idx)
            else:
                logging.getLogger(__name__).warning(
                    f"Skipping layout detection on page {page_idx} "
                    f"({w}x{h}px = {w*h/1e6:.1f}MP) — too large for safe processing")

        return {
            "page": page_idx,
            "text": final_text,
            "text_source": text_source,
            "tables": tables,
            "layout_blocks": layout_blocks,
        }

    def _heuristic_table_check(self, text: str) -> bool:
        # 1. "Table" keyword
        if "Table" in text or "table" in text:
            return True
        # 2. Sparse lines / columns (advanced heuristic could go here)
        # Checking for lines with high non-alpha ratio?
        lines = text.split('\n')
        for ln in lines:
            if len(ln) > 10 and self._is_table_row_candidate(ln):
                return True
        return False

    def _is_table_row_candidate(self, line: str) -> bool:
        # crude check: high digit density or multiple spaces
        digits = sum(c.isdigit() for c in line)
        if digits / len(line) > 0.3:
            return True
        if "  " in line: # multiple spaces
            return True
        return False



    def _extract_tables_gmft(self, pdf_path: str, page_idx: int) -> List[Dict]:
        if not GMFT_AVAILABLE or not getattr(self, "gmft_detector", None): return []
        # optimization: store gmft results in self temporarily?
        # For now, simplistic call (overhead warning)
        # Proper way: GMFT can accept a specific page? 
        # detector.extract(path) -> tables.
        # We can implement a "get_tables_for_doc" cached method.
            
        # Check cache
        if pdf_path not in self._doc_tables_cache:
             # This runs on whole doc. 
             # If we only want to run it if *this* page needs it, 
             # we accept the hit on the first "table-like" page.
             try:
                 from gmft.pdf_bindings import PyPDFium2Document
                 doc = PyPDFium2Document(pdf_path)
                 tables = []
                 for page in doc:
                     tables.extend(self.gmft_detector.extract(page))
                 self._doc_tables_cache[pdf_path] = tables
                 doc.close()
             except Exception as e:
                 logging.getLogger(__name__).warning(f"GMFT extraction failed: {e}")
                 self._doc_tables_cache[pdf_path] = []
        
        all_tables = self._doc_tables_cache[pdf_path]
        page_tables = [t for t in all_tables if getattr(t, "page_num", -1) == page_idx] # GMFT uses 0-indexed? Check docs. Usually 0-based in python wrappers.
        
        out = []
        for t in page_tables:
            try:
                ft = self.gmft_formatter.extract(t)
                csv = ft.df().to_csv(index=False)
                out.append({"csv": csv, "bbox": getattr(t, "bbox", [])})
            except Exception as e:
                logging.getLogger(__name__).warning(f"GMFT formatting failed for table on page {page_idx}: {e}")
                pass
        return out

    # ---- Surya-based layout block detection ----

    def _detect_layout_blocks(
        self, page_image: Image.Image, page_idx: int
    ) -> List[Dict[str, Any]]:
        """Run Surya layout prediction and crop Table/Figure regions.

        Bounding-box coordinates are clamped to the actual page dimensions so
        that partially-offscreen elements never cause a PIL crop error.

        Returns a list of dicts, each containing:
            type          – "Table" or "Figure"
            bbox          – [x0, y0, x1, y1] in pixel coords
            page          – 0-indexed page number
            cropped_image – PIL.Image of the isolated region
        """
        if self.layout_predictor is None:
            return []

        TARGET_LABELS = {"Table", "Figure", "Picture", "Chart"}
        page_w, page_h = page_image.size
        blocks: List[Dict[str, Any]] = []

        try:
            predictions = self.layout_predictor([page_image])
            # Surya returns a list (one per input image); take the first.
            page_pred = predictions[0]

            for block in page_pred.bboxes:
                label = block.label
                if label not in TARGET_LABELS:
                    continue

                # Normalize label to the two canonical types
                canonical_type = "Table" if label == "Table" else "Figure"

                # Raw bbox from Surya: [x0, y0, x1, y1] in pixel space
                raw = block.bbox
                x0 = max(0, min(int(raw[0]), page_w))
                y0 = max(0, min(int(raw[1]), page_h))
                x1 = max(0, min(int(raw[2]), page_w))
                y1 = max(0, min(int(raw[3]), page_h))

                # Skip degenerate boxes (zero-area after clamping)
                if x1 <= x0 or y1 <= y0:
                    continue

                cropped = page_image.crop((x0, y0, x1, y1))

                blocks.append({
                    "type": canonical_type,
                    "bbox": [x0, y0, x1, y1],
                    "page": page_idx,
                    "cropped_image": cropped,
                })

        except Exception:
            # Layout prediction failed for this page — degrade gracefully.
            pass

        return blocks
