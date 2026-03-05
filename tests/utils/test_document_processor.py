import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.document_processor import DocumentProcessor, ProcessorConfig, DiskCache, downscale_pil

class TestDocumentProcessor:
    @pytest.fixture
    def config(self):
        return ProcessorConfig(
            cache_dir=".cache/test_docproc",
            table_mode="auto",
            pdf_backend="pymupdf"
        )

    def test_init_and_cache(self, config):
        """Test basic initialization and cache setup."""
        with patch("src.utils.document_processor.SURYA_AVAILABLE", False), \
             patch("src.utils.document_processor.GMFT_AVAILABLE", False):
            processor = DocumentProcessor(config)
            assert processor.cache.cache_dir == ".cache/test_docproc"
            assert processor.cfg.table_mode == "auto"

    def test_downscale_pil(self):
        """Test image downscaling logic."""
        im = MagicMock()
        im.size = (4000, 3000)
        im.resize.return_value = "resized_image"

        result = downscale_pil(im, 2048)
        im.resize.assert_called_once_with((2048, 1536))
        assert result == "resized_image"

        # Test no upscaling
        im.size = (1000, 800)
        im.resize.reset_mock()
        result = downscale_pil(im, 2048)
        assert result == im
        im.resize.assert_not_called()

    @patch("src.utils.document_processor.stable_file_hash")
    @patch("src.utils.document_processor.FitzAdapter")
    def test_process_pdf_cached(self, mock_fitz, mock_hash, config):
        """Test that process_pdf returns cached result if available."""
        processor = DocumentProcessor(config)
        processor.cache.get = MagicMock(return_value={"cached": "data"})
        
        result = processor.process_pdf("test.pdf")
        assert result == {"cached": "data"}
        mock_fitz.assert_not_called()

    @patch("src.utils.document_processor.stable_file_hash", return_value="hash123")
    @patch("src.utils.document_processor.FitzAdapter")
    def test_process_pdf_happy_path(self, mock_fitz_class, mock_hash, config):
        """Test full PDF processing happy path."""
        processor = DocumentProcessor(config)
        processor.cache.get = MagicMock(return_value=None)
        processor.cache.set = MagicMock()
        
        mock_adapter = MagicMock()
        mock_adapter.get_page_count.return_value = 2
        mock_fitz_class.return_value = mock_adapter

        # Mock page processing
        processor._process_page = MagicMock(side_effect=[
            {"page": 0, "text": "Page 1", "text_source": "digital", "tables": []},
            {"page": 1, "text": "Page 2", "text_source": "ocr", "tables": []}
        ])

        result = processor.process_pdf("test.pdf")
        
        assert result["doc_pages"] == 2
        assert result["content"] == "Page 1\n\nPage 2"
        processor.cache.set.assert_called_once()
        mock_adapter.close.assert_called_once()

    @patch("src.utils.document_processor.stable_file_hash", return_value="hash123")
    @patch("src.utils.document_processor.FitzAdapter")
    def test_process_pdf_handles_recursion_error(self, mock_fitz_class, mock_hash, config):
        """Test PDF processing catches RecursionError per page."""
        processor = DocumentProcessor(config)
        processor.cache.get = MagicMock(return_value=None)
        
        mock_adapter = MagicMock()
        mock_adapter.get_page_count.return_value = 1
        mock_fitz_class.return_value = mock_adapter

        processor._process_page = MagicMock(side_effect=RecursionError("Circular ref"))

        result = processor.process_pdf("test.pdf")
        
        assert result["pages"][0]["text_source"] == "error"
        assert result["pages"][0]["text"] == ""
        
    @patch("src.utils.document_processor.stable_file_hash", return_value="hash123")
    @patch("src.utils.document_processor.PdfiumAdapter")
    def test_process_pdf_pdfium_backend(self, mock_pdfium_class, mock_hash, config):
        """Test process_pdf uses pypdfium2 when configured."""
        config.pdf_backend = "pypdfium2"
        processor = DocumentProcessor(config)
        processor.cache.get = MagicMock(return_value=None)
        processor.cache.set = MagicMock()
        
        mock_adapter = MagicMock()
        mock_adapter.get_page_count.return_value = 1
        mock_pdfium_class.return_value = mock_adapter

        processor._process_page = MagicMock(return_value={"page": 0, "text": "Page 1", "text_source": "digital", "tables": []})

        result = processor.process_pdf("test.pdf")
        
        mock_pdfium_class.assert_called_once()
        mock_adapter.close.assert_called_once()

    @patch("src.utils.document_processor.SURYA_AVAILABLE", True)
    @patch("src.utils.document_processor.LayoutPredictor", side_effect=Exception("Surya failed"), create=True)
    def test_surya_init_exception(self, mock_surya, config):
        with patch("logging.getLogger") as mock_logger:
            processor = DocumentProcessor(config)
            assert processor.layout_predictor is None
            mock_logger.return_value.warning.assert_called_once()

    @patch("src.utils.document_processor.GMFT_AVAILABLE", True)
    @patch("src.utils.document_processor.AutoTableDetector", side_effect=Exception("GMFT detector failed"), create=True)
    def test_gmft_init_exception(self, mock_gmft, config):
        config.table_mode = "auto"
        with patch("logging.getLogger") as mock_logger:
            processor = DocumentProcessor(config)
            assert processor.gmft_detector is None
            assert processor.gmft_formatter is None
            mock_logger.return_value.warning.assert_called_once()

    def test_heuristic_table_check(self, config):
        """Test table heuristic detection."""
        processor = DocumentProcessor(config)
        assert processor._heuristic_table_check("This is a Table.") == True
        assert processor._heuristic_table_check("table 1 shows results.") == True
        # Test digit density
        assert processor._heuristic_table_check("0.1 0.2 0.3 0.4 0.5 0.6 0.7") == True
        assert processor._heuristic_table_check("plain text with no tabular data") == False

    def test_process_page_digital_gate(self, config):
        """Test that digital text skips OCR."""
        processor = DocumentProcessor(config)
        adapter = MagicMock()
        # Create text with enough words and chars and UNIQUE chars to pass digital gate
        text = "word " * 30 + "abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 5
        adapter.get_page_text.return_value = text
        adapter.render_page = MagicMock()

        processor._heuristic_table_check = MagicMock(return_value=False)

        result = processor._process_page(adapter, 0, "test.pdf")
        
        assert result["text_source"] == "digital"
        assert result["text"] == text
        adapter.render_page.assert_not_called()

    def test_process_page_ocr_fallback(self, config):
        """Test OCR fallback when text is not digital."""
        processor = DocumentProcessor(config)
        adapter = MagicMock()
        adapter.get_page_text.return_value = "Short text"
        
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        adapter.render_page.return_value = mock_img
        
        mock_tesseract = MagicMock()
        mock_tesseract.image_to_string.return_value = "OCR Text"

        with patch.dict("sys.modules", {"pytesseract": mock_tesseract}):
            result = processor._process_page(adapter, 0, "test.pdf")
        
        assert result["text_source"] == "ocr"
        assert result["text"] == "OCR Text"

    def test_process_page_gmft_crash_handled(self, config):
        """Test that GMFT formatting crash is caught gracefully."""
        # Force table mode
        config.table_mode = "force"
        processor = DocumentProcessor(config)
        
        processor.gmft_detector = MagicMock()
        processor.gmft_formatter = MagicMock()
        
        fake_table = MagicMock()
        fake_table.page_num = 0
        processor._doc_tables_cache = {"fake.pdf": [fake_table]}
        
        processor.gmft_formatter.extract.side_effect = NotImplementedError("Cannot copy out of meta tensor; no data!")
        
        adapter = MagicMock()
        adapter.get_page_text.return_value = "Short text"
        fake_img = MagicMock()
        fake_img.size = (800, 600)
        adapter.render_page.return_value = fake_img
        
        # Patch tesseract to avoid OCR issues
        with patch("src.utils.document_processor.pytesseract", create=True):
            result = processor._process_page(adapter, 0, "fake.pdf")
        
        assert result["page"] == 0
        assert result["tables"] == [], "The crashing table should be gracefully skipped"

    @patch("src.utils.document_processor.stable_file_hash", return_value="hash123")
    @patch("src.utils.document_processor.FitzAdapter")
    def test_process_page_generic_exception(self, mock_fitz_class, mock_hash, config):
        """Test catching a generic exception during page processing."""
        processor = DocumentProcessor(config)
        processor.cache.get = MagicMock(return_value=None)
        
        mock_adapter = MagicMock()
        mock_adapter.get_page_count.return_value = 1
        mock_fitz_class.return_value = mock_adapter

        processor._process_page = MagicMock(side_effect=RuntimeError("Something completely unexpected"))
        
        result = processor.process_pdf("test.pdf")
        
        assert result["pages"][0]["text_source"] == "error_catchall"
        assert result["pages"][0]["text"] == ""
        assert result["pages"][0]["tables"] == []

    def test_process_page_branch_coverage_ocr_fallback(self, config):
        """Hit the non-digital, missing Tesseract branch and table_mode == 'off'."""
        config.table_mode = "off"
        # Increase these so our dummy string definitely fails the threshold
        config.min_digital_chars = 10
        config.min_digital_words = 5 
        processor = DocumentProcessor(config)
        
        adapter = MagicMock()
        # > 10 chars, but only 1 word. Fails is_digital.
        adapter.get_page_text.return_value = "a" * 100 
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        adapter.render_page.return_value = mock_img
        
        # Force pytesseract ImportError
        with patch.dict("sys.modules", {"pytesseract": None}):
            result = processor._process_page(adapter, 0, "fake.pdf")
            
        assert result["text_source"] == "ocr"
        assert result["tables"] == []
        assert result["text"] == "a" * 100

    def test_process_page_branch_coverage_digital_layout(self, config):
        """Hit the is_digital=True, table heuristic=False, layout_predictor=present branches."""
        config.table_mode = "auto"
        config.min_digital_chars = 10
        config.min_digital_words = 5
        config.min_unique_ratio = 0.1
        processor = DocumentProcessor(config)
        processor.layout_predictor = MagicMock()
        processor._heuristic_table_check = MagicMock(return_value=False)
        processor._detect_layout_blocks = MagicMock(return_value=["mock_block"])
        
        adapter = MagicMock()
        adapter.get_page_text.return_value = "This is a normal digital text sequence with many words."
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        adapter.render_page.return_value = mock_img
        
        result = processor._process_page(adapter, 0, "fake.pdf")
        
        assert result["text_source"] == "digital"
        assert result["tables"] == []
        assert result["layout_blocks"] == ["mock_block"]
        processor._detect_layout_blocks.assert_called_once()
        # Ensure it was forced to render the page image for layout detection
        adapter.render_page.assert_called_once()

    def test_detect_layout_blocks(self, config):
        """Test Surya layout prediction parsing and cropping."""
        processor = DocumentProcessor(config)
        processor.layout_predictor = MagicMock()
        
        # Mock surya prediction
        mock_pred = MagicMock()
        # Box 1: Table, Box 2: Figure, Box 3: Ignore
        box1 = MagicMock(); box1.label = "Table"; box1.bbox = [10, 10, 50, 50]
        box2 = MagicMock(); box2.label = "Figure"; box2.bbox = [100, 100, 200, 200]
        box3 = MagicMock(); box3.label = "Text"; box3.bbox = [0, 0, 10, 10]
        mock_pred.bboxes = [box1, box2, box3]
        
        processor.layout_predictor.return_value = [mock_pred]
        
        img = MagicMock()
        img.size = (1000, 1000)
        img.crop.return_value = "cropped_img"
        
        blocks = processor._detect_layout_blocks(img, 0)
        
        assert len(blocks) == 2
        assert blocks[0]["type"] == "Table"
        assert blocks[0]["bbox"] == [10, 10, 50, 50]
        assert blocks[1]["type"] == "Figure"

class TestPDFAdaptersAndUtils:
    def test_fitz_adapter(self):
        from src.utils.document_processor import FitzAdapter
        mock_fitz = MagicMock()
        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            adapter = FitzAdapter()
            assert adapter.fitz == mock_fitz
            
            adapter.open("test.pdf")
            mock_fitz.open.assert_called_with("test.pdf")
            
            mock_doc = MagicMock()
            adapter.doc = mock_doc
            
            mock_page = MagicMock()
            mock_doc.load_page.return_value = mock_page
            mock_page.get_text.return_value = "page text"
            assert adapter.get_page_text(0) == "page text"
            
            mock_pix = MagicMock()
            mock_pix.tobytes.return_value = b'fake_png'
            mock_page.get_pixmap.return_value = mock_pix
            
            with patch("src.utils.document_processor.Image.open") as mock_img_open:
                mock_img = MagicMock()
                mock_img_open.return_value.convert.return_value = mock_img
                assert adapter.render_page(0, 144) == mock_img
                mock_img_open.assert_called_once()
            
            mock_doc.page_count = 5
            assert adapter.get_page_count() == 5
            
            adapter.close()
            mock_doc.close.assert_called_once()
        
    def test_pdfium_adapter(self):
        from src.utils.document_processor import PdfiumAdapter
        mock_pdfium = MagicMock()
        with patch.dict("sys.modules", {"pypdfium2": mock_pdfium}):
            adapter = PdfiumAdapter()
            assert adapter.pdfium == mock_pdfium
            
            adapter.open("test.pdf")
            mock_pdfium.PdfDocument.assert_called_with("test.pdf")
            
            mock_doc = MagicMock()
            adapter.doc = mock_doc
            
            mock_page = MagicMock()
            mock_doc.get_page.return_value = mock_page
            mock_page.get_textpage.return_value.get_text_range.return_value = "page text"
            assert adapter.get_page_text(0) == "page text"
            
            mock_bitmap = MagicMock()
            mock_page.render.return_value = mock_bitmap
            mock_img = MagicMock()
            mock_bitmap.to_pil.return_value.convert.return_value = mock_img
            assert adapter.render_page(0, 144) == mock_img
            mock_page.render.assert_called_with(scale=2.0, rotation=0)

            mock_doc.__len__.return_value = 5
            assert adapter.get_page_count() == 5
            
            adapter.close()
            mock_doc.close.assert_called_once()
            
    def test_pdf_adapter_base(self):
        from src.utils.document_processor import PDFAdapter
        class DummyAdapter(PDFAdapter):
            def open(self, path): super().open(path)
            def close(self): super().close()
            def get_page_count(self): super().get_page_count()
            def get_page_text(self, page_index): super().get_page_text(page_index)
            def render_page(self, page_index, dpi): super().render_page(page_index, dpi)
        
        adapter = DummyAdapter()
        adapter.open("test.pdf")
        adapter.close()
        adapter.get_page_count()
        adapter.get_page_text(0)
        adapter.render_page(0, 144)
            
    def test_fitz_import_error(self):
        from src.utils.document_processor import FitzAdapter
        with patch.dict("sys.modules", {"fitz": None}):
            with pytest.raises(ImportError):
                FitzAdapter()
                
    def test_pdfium_import_error(self):
        from src.utils.document_processor import PdfiumAdapter
        with patch.dict("sys.modules", {"pypdfium2": None}):
            with pytest.raises(ImportError):
                PdfiumAdapter()
        
    def test_disk_cache(self, tmp_path):
        from src.utils.document_processor import DiskCache
        cache_dir = tmp_path / "test_cache"
        cache = DiskCache(str(cache_dir))
        
        # Test miss
        assert cache.get("missing_key") is None
        
        # Test set and get
        cache.set("my_key", {"data": 123})
        assert cache.get("my_key") == {"data": 123}
        
    def test_stable_file_hash(self, tmp_path):
        from src.utils.document_processor import stable_file_hash
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        
        hash_val = stable_file_hash(str(test_file))
        assert hash_val == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    @patch("src.utils.document_processor.GMFT_AVAILABLE", True)
    def test_extract_tables_gmft_caching(self):
        """Test the GMFT PyPDFium2Document parsing and caching logic."""
        from src.utils.document_processor import ProcessorConfig
        config = ProcessorConfig(cache_dir=".cache/test_docproc", table_mode="auto", pdf_backend="pymupdf")
        processor = DocumentProcessor(config)
        processor.gmft_detector = MagicMock()
        processor.gmft_formatter = MagicMock()
        
        mock_t1 = MagicMock()
        mock_t1.page_num = 0
        processor.gmft_detector.extract.return_value = [mock_t1]
        
        mock_formatted = MagicMock()
        mock_formatted.df.return_value.to_csv.return_value = "col1,col2"
        processor.gmft_formatter.extract.return_value = mock_formatted
        
        # Test uncached
        mock_gmft_module = MagicMock()
        mock_doc_inst = MagicMock()
        mock_doc_inst.__iter__.return_value = ["page_obj"]
        mock_gmft_module.PyPDFium2Document.return_value = mock_doc_inst
        
        with patch.dict("sys.modules", {"gmft": MagicMock(), "gmft.pdf_bindings": mock_gmft_module}):
            out = processor._extract_tables_gmft("test.pdf", 0)
            
            assert len(out) == 1
            assert out[0]["csv"] == "col1,col2"
            assert "test.pdf" in processor._doc_tables_cache
            
            # Test cached (should not reload)
            mock_gmft_module.PyPDFium2Document.reset_mock()
            out2 = processor._extract_tables_gmft("test.pdf", 0)
            mock_gmft_module.PyPDFium2Document.assert_not_called()
            assert len(out2) == 1

    @patch("src.utils.document_processor.GMFT_AVAILABLE", True)
    def test_extract_tables_gmft_exception(self):
        """Test that _extract_tables_gmft catches and logs general exceptions."""
        from src.utils.document_processor import ProcessorConfig
        config = ProcessorConfig(cache_dir=".cache/test_docproc", table_mode="auto", pdf_backend="pymupdf")
        processor = DocumentProcessor(config)
        
        mock_gmft_module = MagicMock()
        mock_gmft_module.PyPDFium2Document.side_effect = ValueError("PDF load failed")
        
        with patch.dict("sys.modules", {"gmft": MagicMock(), "gmft.pdf_bindings": mock_gmft_module}), \
             patch("logging.getLogger") as mock_get_logger:
                 
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            out = processor._extract_tables_gmft("broken.pdf", 0)
            
            assert out == []
            mock_logger.warning.assert_called_once()
            assert "broken.pdf" in processor._doc_tables_cache
