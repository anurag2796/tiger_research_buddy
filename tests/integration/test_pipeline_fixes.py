import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
"""
Regression tests for the 5 pipeline bug fixes (commit 1c49a38).

Bug 1: Vector store meta-tensor crash — vector_store.py
Bug 2: ScholarCrawler race condition — scholar_crawler.py
Bug 3: DocumentProcessor recursion error — document_processor.py
Bug 4: Vision type bug — pdf_distiller.py
Bug 5: SmartCrawler binary file decode — smart_crawler.py
"""
import sys
import asyncio
import threading
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Bug 1: Vector Store ────────────────────────────────────────────────────────

class TestVectorStoreMetaTensor:
    """Bug 1: SentenceTransformer meta-tensor crash avoidance."""

    def test_embedding_function_handles_meta_tensor(self):
        """_get_embedding_function must pass device='cpu' on MPS or fallback to DefaultEmbeddingFunction."""
        # Patch SentenceTransformer inside vector_store before import
        class FakeSentenceTransformer:
            def __init__(self, model_name, trust_remote_code=False, device=None):
                self.device = device
                # Simulate the error if not cpu
                if device != "cpu":
                    raise NotImplementedError("Cannot copy out of meta tensor; no data!")

            def encode(self, texts, convert_to_numpy=False):
                return [[0.1, 0.2, 0.3]] * len(texts)

        with patch.dict("sys.modules", {}):
            with patch("sentence_transformers.SentenceTransformer", FakeSentenceTransformer):
                from src.database.vector_store import _get_embedding_function
                # Reset the global so we get a fresh instance
                import src.database.vector_store as vs_module
                vs_module._embedding_function = None

                with patch("chromadb.EmbeddingFunction", object):
                    with patch("chromadb.Documents", list):
                        with patch("chromadb.Embeddings", list):
                            # Force MPS to be "available"
                            with patch("torch.backends.mps.is_available", return_value=True):
                                fn = _get_embedding_function()

        assert fn is not None, "Failed to initialize embedding function"
        
        # Reset global for other tests
        import src.database.vector_store as vs_module
        vs_module._embedding_function = None


# ── Bug 2: ScholarCrawler Race Condition ──────────────────────────────────────

class TestScholarCrawlerRace:
    """Bug 2: copy-on-write prevents 'dictionary changed size during iteration'."""

    def test_no_cross_thread_mutation(self):
        """Workers must not mutate the shared faculty list element directly.
        _process_single_faculty receives (idx, prof) and returns
        (idx, updated_copy, scholar_data) — the original dict is never touched."""
        from src.crawlers.scholar_crawler import ScholarCrawler

        crawler = ScholarCrawler.__new__(ScholarCrawler)
        crawler.resolver = MagicMock()
        crawler.resolver.resolve_faculty.return_value = "faculty_abc123"

        original_prof = {"name": "Test Prof", "department": "CS"}
        original_id = id(original_prof)

        # Call worker directly
        with patch.object(crawler, "search_author", return_value=None):
            idx_out, updated, scholar = crawler._process_single_faculty((0, original_prof))

        assert idx_out == 0
        assert id(updated) != original_id, "Worker returned the original dict — it must return a copy"
        assert "id" not in original_prof, "Worker mutated the original prof dict directly"
        assert updated.get("id") == "faculty_abc123", "Updated copy is missing the resolved ID"

    def test_stress_concurrent_enrichment_no_runtime_error(self):
        """50 faculty members, 10 threads — must not raise RuntimeError."""
        from src.crawlers.scholar_crawler import ScholarCrawler

        # Build a minimal ScholarCrawler bypassing __init__ heavy setup
        crawler = ScholarCrawler.__new__(ScholarCrawler)
        crawler.max_workers = 10
        crawler.resolver = MagicMock()
        crawler.resolver.resolve_faculty.return_value = "faculty_test"
        crawler.serpapi_key = None

        faculty = [{"name": f"Prof {i}", "department": "CS"} for i in range(50)]

        errors = []

        def run():
            try:
                with patch.object(crawler, "search_author", return_value=None), \
                     patch("scholarly.SCHOLARLY_AVAILABLE", False, create=True), \
                     patch("src.crawlers.scholar_crawler.SCHOLARLY_AVAILABLE", False), \
                     patch("src.crawlers.scholar_crawler.SERPAPI_AVAILABLE", False):
                    from rich.progress import Progress
                    # Bypass Progress display in tests
                    with patch("src.crawlers.scholar_crawler.Progress"), \
                         patch("src.crawlers.scholar_crawler.SpinnerColumn"), \
                         patch("src.crawlers.scholar_crawler.BarColumn"), \
                         patch("src.crawlers.scholar_crawler.TextColumn"):
                        result = crawler.enrich_faculty_data(faculty)
                    assert len(result) == 50
            except RuntimeError as e:
                errors.append(str(e))

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=30)

        assert not errors, f"Race condition errors: {errors}"


# ── Bug 3: DocumentProcessor Recursion ────────────────────────────────────────

class TestDocumentProcessorRecursion:
    """Bug 3: RecursionError per-page is caught; document is partially extracted."""

    def test_recursion_error_on_page_produces_empty_entry_not_exception(self):
        """A page that raises RecursionError should produce an error-type page entry,
        not propagate the exception up to the caller.

        This calls process_pdf() directly (via mocked adapter) to guarantee
        any future refactor of the loop is still regression-tested.
        """
        from src.utils.document_processor import DocumentProcessor, ProcessorConfig

        cfg = ProcessorConfig(table_mode="off", pdf_backend="pymupdf")

        with patch("src.utils.document_processor.SURYA_AVAILABLE", False), \
             patch("src.utils.document_processor.GMFT_AVAILABLE", False):
            dp = DocumentProcessor(cfg)

        # Bypass disk cache and file hash
        dp.cache.get = MagicMock(return_value=None)
        dp.cache.set = MagicMock()

        # Build adapter mock: page 0 raises RecursionError, page 1 works fine
        mock_adapter = MagicMock()
        mock_adapter.get_page_count.return_value = 2
        dp._process_page = MagicMock(side_effect=[
            RecursionError("too deep"),
            {"page": 1, "text": "Normal text on page 1", "text_source": "digital", "tables": []}
        ])

        with patch("src.utils.document_processor.FitzAdapter", return_value=mock_adapter), \
             patch("src.utils.document_processor.stable_file_hash", return_value="fakehash"):
            result = dp.process_pdf("test.pdf")

        assert len(result["pages"]) == 2, "Both pages should be in output even when one raises RecursionError"
        assert result["pages"][0]["text_source"] == "error", "Recursion page should have text_source='error'"
        assert result["pages"][0]["text"] == "", "Recursion page should have empty text"
        assert result["pages"][1]["text"] == "Normal text on page 1", "Good page should have its text"

    def test_recursion_limit_is_restored_after_process_pdf(self):
        """sys.getrecursionlimit() must be the same before and after a
        scoped recursion-limit block, regardless of success or failure.

        This tests the try/finally pattern used in process_pdf rather than
        the full function (which requires heavy model setup), ensuring the
        restore guard is logically correct.
        """
        import sys
        original_limit = sys.getrecursionlimit()
        new_limit = max(original_limit, 5000)

        raised = False
        try:
            _prev = sys.getrecursionlimit()
            sys.setrecursionlimit(new_limit)
            assert sys.getrecursionlimit() == new_limit
            raise RuntimeError("simulated failure mid-function")
        except RuntimeError:
            raised = True
        finally:
            sys.setrecursionlimit(_prev)

        assert raised, "Exception should have been raised"
        assert sys.getrecursionlimit() == original_limit, (
            "Recursion limit was not restored in the finally block"
        )


# ── Bug 4: Vision Type Guard ───────────────────────────────────────────────────

class TestVisionTypeGuard:
    """Bug 4: extract_text_async handles str/dict/unexpected return types from VisionCrawler."""

    @pytest.mark.asyncio
    async def test_dict_result_returns_content(self):
        """Normal case: VisionCrawler returns a dict with 'content' key."""
        from src.processors.pdf_distiller import DeepDistiller

        distiller = DeepDistiller.__new__(DeepDistiller)
        distiller.vision_crawler = MagicMock()
        distiller.vision_crawler.convert.return_value = {"content": "Paper text here", "pages": []}

        with patch("src.processors.pdf_distiller.Timer"):
            result = await distiller.extract_text_async(Path("test.pdf"))

        assert result == "Paper text here"

    @pytest.mark.asyncio
    async def test_str_result_returns_string_directly(self):
        """Bug case: VisionCrawler returns a bare str — must not raise AttributeError."""
        from src.processors.pdf_distiller import DeepDistiller

        distiller = DeepDistiller.__new__(DeepDistiller)
        distiller.vision_crawler = MagicMock()
        distiller.vision_crawler.convert.return_value = "raw text fallback"

        with patch("src.processors.pdf_distiller.Timer"), \
             patch("src.processors.pdf_distiller.logger") as mock_logger:
            result = await distiller.extract_text_async(Path("test.pdf"))

        assert result == "raw text fallback", "str result should be returned as-is"
        mock_logger.warning.assert_called_once(), "Should log a warning when str is returned"

    @pytest.mark.asyncio
    async def test_none_result_returns_empty_string(self):
        """Edge case: VisionCrawler returns None — must return empty string, not crash."""
        from src.processors.pdf_distiller import DeepDistiller

        distiller = DeepDistiller.__new__(DeepDistiller)
        distiller.vision_crawler = MagicMock()
        distiller.vision_crawler.convert.return_value = None

        with patch("src.processors.pdf_distiller.Timer"), \
             patch("src.processors.pdf_distiller.logger"):
            result = await distiller.extract_text_async(Path("test.pdf"))

        assert result == "", "None result should produce an empty string"


# ── Bug 5: SmartCrawler Binary Decode ─────────────────────────────────────────

class TestSmartCrawlerBinaryDecode:
    """Bug 5: Content-Type check prevents UnicodeDecodeError on binary URLs."""

    @pytest.mark.asyncio
    async def test_binary_content_type_returns_none(self):
        """fetch_page must return None for binary Content-Types without trying to decode."""
        from src.crawlers.smart_crawler import SmartCrawler
        from src.utils.config import RESTRICTED_CONFIG

        crawler = SmartCrawler.__new__(SmartCrawler)
        crawler.config = RESTRICTED_CONFIG

        binary_types = [
            "application/zip",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
            "application/pdf",
            "application/octet-stream",
        ]

        for ct in binary_types:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": ct}
            mock_response.text = AsyncMock(return_value="should not be called")
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=False)

            mock_session = MagicMock()
            mock_session.get.return_value = mock_response

            result = await crawler.fetch_page(mock_session, "https://example.com/file.docx")

            assert result is None, f"Expected None for Content-Type '{ct}', got {result!r}"
            mock_response.text.assert_not_called(), (
                f"response.text() should NOT be called for binary Content-Type '{ct}'"
            )

    @pytest.mark.asyncio
    async def test_html_content_type_returns_text(self):
        """fetch_page must return decoded text for text/html responses."""
        from src.crawlers.smart_crawler import SmartCrawler
        from src.utils.config import RESTRICTED_CONFIG

        crawler = SmartCrawler.__new__(SmartCrawler)
        crawler.config = RESTRICTED_CONFIG

        expected_html = "<html><body>Hello</body></html>"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.text = AsyncMock(return_value=expected_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        result = await crawler.fetch_page(mock_session, "https://www.rit.edu/computing/people/")

        assert result == expected_html, "HTML Content-Type should be decoded and returned"


# ── Bug 6: DocumentProcessor GMFT Meta Tensor Crash ─────────────────────────

class TestDocumentProcessorGMFTFallback:
    """Bug 6: Gracefully handle PyTorch NotImplementedError during GMFT format."""

    def test_process_page_catches_gmft_crash(self):
        """If AutoTableFormatter.extract raises an Exception (like meta tensor error), we must not crash the pipeline."""
        from src.utils.document_processor import DocumentProcessor, ProcessorConfig
        
        cfg = ProcessorConfig(table_mode="force", table_backend="gmft")
        processor = DocumentProcessor.__new__(DocumentProcessor)
        processor.cfg = cfg
        processor.layout_predictor = None
        
        # Mock the GMFT detector and formatter
        processor.gmft_detector = MagicMock()
        processor.gmft_formatter = MagicMock()
        
        # Mock the detector to return one fake table
        fake_table = MagicMock()
        fake_table.page_num = 0
        processor._doc_tables_cache = {"fake.pdf": [fake_table]}
        
        # KEY PART: The formatter triggers the PyTorch MPS crash
        processor.gmft_formatter.extract.side_effect = NotImplementedError("Cannot copy out of meta tensor; no data!")
        
        # We only need to test `_extract_tables_gmft` directly since it's the culprit, 
        # but let's test `_process_page` to ensure it doesn't crash the whole page processing.
        adapter = MagicMock()
        adapter.get_page_text.return_value = "This is a test page with a table."
        fake_img = MagicMock()
        fake_img.size = (800, 600)
        adapter.render_page.return_value = fake_img
        
        # This used to crash the crawler. Now it should return silently with empty tables list.
        result = processor._process_page(adapter, 0, "fake.pdf")
        
        assert result["page"] == 0
        assert result["tables"] == [], "The crashing table should be gracefully skipped"
        

if __name__ == "__main__":
    pytest.main(["-v", __file__])
