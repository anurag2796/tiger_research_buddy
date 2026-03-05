import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
"""
Integration tests for DocumentProcessor using real PDFs from the project's data directory.

These tests validate that the pipeline handles actual research papers correctly,
not just mocked data. Strategically selected PDFs cover:
  - Small/fast digital text (brent_fast_and_accurate...)
  - The exact PDF that caused the original restricted-mode crash (connor_language_models...)
  - A table/figure-heavy paper (pengcheng_hierarchical_semantic...)

Run: pytest tests/test_document_processor_integration.py -v
"""
import os
import sys
import time
import json
import pytest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.document_processor import DocumentProcessor, ProcessorConfig

# ── Test Data Paths ───────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
RESTRICTED_PDF_DIR = PROJECT_ROOT / "data" / "restricted" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Strategic PDF selections
SMALL_PDF = RESTRICTED_PDF_DIR / "brent_fast_and_accurate_alignment_of_long_bisulfite-seq_reads.pdf"
CRASH_PDF = RESTRICTED_PDF_DIR / "connor_language_models_as_emotional_classifiers_for_textual_convers.pdf"
TABLE_PDF = RESTRICTED_PDF_DIR / "pengcheng_hierarchical_semantic_learning_for_multi-class_aorta_segment.pdf"

# Fallback: pick any available PDF if the specific ones are missing
def _find_any_pdf():
    for d in [RESTRICTED_PDF_DIR, PDF_DIR]:
        if d.exists():
            pdfs = list(d.glob("*.pdf"))
            if pdfs:
                return sorted(pdfs, key=lambda p: p.stat().st_size)[0]
    return None

HAS_SMALL_PDF = SMALL_PDF.exists()
HAS_CRASH_PDF = CRASH_PDF.exists()
HAS_TABLE_PDF = TABLE_PDF.exists()
HAS_ANY_PDF = HAS_SMALL_PDF or HAS_CRASH_PDF or HAS_TABLE_PDF or (_find_any_pdf() is not None)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def processor(tmp_path):
    """Create a DocumentProcessor with isolated cache in tmp_path."""
    cfg = ProcessorConfig(
        cache_dir=str(tmp_path / "integration_cache"),
        table_mode="off",
        pdf_backend="pymupdf",
    )
    with patch("src.utils.document_processor.SURYA_AVAILABLE", False):
        proc = DocumentProcessor(cfg)
    return proc


@pytest.fixture
def processor_with_tables(tmp_path):
    """Processor with table detection enabled (for table-heavy PDFs)."""
    cfg = ProcessorConfig(
        cache_dir=str(tmp_path / "integration_cache_tables"),
        table_mode="auto",
        pdf_backend="pymupdf",
    )
    with patch("src.utils.document_processor.SURYA_AVAILABLE", False):
        proc = DocumentProcessor(cfg)
    return proc


# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_output_structure(result, pdf_path_str):
    """Assert the output dict from process_pdf has the correct shape."""
    assert isinstance(result, dict), "Result should be a dict"

    assert "pdf_path" in result, "Missing 'pdf_path'"
    assert "doc_pages" in result, "Missing 'doc_pages'"
    assert "pages" in result, "Missing 'pages'"
    assert "content" in result, "Missing 'content'"
    assert "metadata" in result, "Missing 'metadata'"
    assert "elapsed_s" in result, "Missing 'elapsed_s'"

    assert result["pdf_path"] == pdf_path_str
    assert isinstance(result["doc_pages"], int)
    assert result["doc_pages"] > 0, "Document should have at least one page"
    assert isinstance(result["pages"], list)
    assert len(result["pages"]) == result["doc_pages"]
    assert isinstance(result["content"], str)

    return result


def validate_page_structure(page):
    """Assert a single page dict has the correct shape and types."""
    assert "page" in page, "Missing 'page' key"
    assert "text" in page, "Missing 'text' key"
    assert "text_source" in page, "Missing 'text_source' key"
    assert "tables" in page, "Missing 'tables' key"

    assert isinstance(page["page"], int)
    assert isinstance(page["text"], str)
    assert page["text_source"] in ("digital", "ocr", "error", "error_catchall"), \
        f"Unexpected text_source: {page['text_source']}"
    assert isinstance(page["tables"], list)


# ── Test Cases ────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not HAS_SMALL_PDF, reason="Small test PDF not found")
class TestRealPDFSmall:
    """Tests using the smallest PDF for fast validation."""

    def test_produces_valid_output(self, processor):
        """Process a real PDF and verify the output structure is correct."""
        result = processor.process_pdf(str(SMALL_PDF))
        validate_output_structure(result, str(SMALL_PDF))

        assert len(result["content"]) > 100, \
            f"Expected substantial text content, got {len(result['content'])} chars"
            
        with open(OUTPUT_DIR / "extracted_small_pdf_content.md", "w") as f:
            f.write(result["content"])

    def test_page_structure_is_valid(self, processor):
        """Every page dict should have the correct keys and types."""
        result = processor.process_pdf(str(SMALL_PDF))

        for page in result["pages"]:
            validate_page_structure(page)

    def test_caching_works(self, processor):
        """Second call should return cached result much faster."""
        t0 = time.time()
        result1 = processor.process_pdf(str(SMALL_PDF))
        first_elapsed = time.time() - t0

        t0 = time.time()
        result2 = processor.process_pdf(str(SMALL_PDF))
        second_elapsed = time.time() - t0

        assert result1["content"] == result2["content"], "Cached content should match"
        assert result1["doc_pages"] == result2["doc_pages"], "Cached page count should match"

        # Cached call should be significantly faster
        assert second_elapsed < first_elapsed, \
            f"Cache miss: first={first_elapsed:.3f}s, second={second_elapsed:.3f}s"

    def test_no_error_pages(self, processor):
        """A well-formed PDF should not produce error pages."""
        result = processor.process_pdf(str(SMALL_PDF))

        error_pages = [p for p in result["pages"]
                       if p["text_source"] in ("error", "error_catchall")]
        assert len(error_pages) == 0, \
            f"Got {len(error_pages)} error pages in a well-formed PDF"


@pytest.mark.skipif(not HAS_CRASH_PDF, reason="Crash-trigger PDF not found")
class TestRealPDFCrashRegression:
    """Tests specifically targeting the PDF that caused the restricted-mode crash.

    connor_language_models_as_emotional_classifiers — the exact paper
    that triggered NotImplementedError in GMFT on MPS backend.
    """

    def test_no_crash_on_restricted_mode_pdf(self, processor):
        """The PDF that originally crashed the pipeline must now process cleanly."""
        result = processor.process_pdf(str(CRASH_PDF))

        validate_output_structure(result, str(CRASH_PDF))
        assert len(result["content"]) > 0, \
            "Crash PDF should produce some text content after fix"
            
        with open(OUTPUT_DIR / "extracted_crash_pdf_content.md", "w") as f:
            f.write(result["content"])

    def test_crash_pdf_page_integrity(self, processor):
        """Every page from the crash PDF should have valid structure."""
        result = processor.process_pdf(str(CRASH_PDF))

        for page in result["pages"]:
            validate_page_structure(page)

        text_pages = [p for p in result["pages"] if p["text"].strip()]
        assert len(text_pages) > 0, \
            "At least some pages should have extracted text"

    def test_crash_pdf_with_table_mode_auto(self, processor_with_tables):
        """Exercise table detection on the crash PDF — this is where the
        original GMFT NotImplementedError occurred."""
        result = processor_with_tables.process_pdf(str(CRASH_PDF))

        validate_output_structure(result, str(CRASH_PDF))

        error_pages = [p for p in result["pages"]
                       if p["text_source"] in ("error", "error_catchall")]
        assert len(error_pages) < result["doc_pages"], \
            "Not all pages should be errors with table detection enabled"


@pytest.mark.skipif(not HAS_TABLE_PDF, reason="Table-heavy PDF not found")
class TestRealPDFTableHeavy:
    """Tests using a figure/table-heavy paper to exercise layout paths."""

    def test_produces_valid_output(self, processor):
        """A table-heavy paper should still produce valid output."""
        result = processor.process_pdf(str(TABLE_PDF))
        validate_output_structure(result, str(TABLE_PDF))

    def test_multi_page_extraction(self, processor):
        """Table-heavy papers are typically longer; verify multi-page handling."""
        result = processor.process_pdf(str(TABLE_PDF))

        assert result["doc_pages"] > 1, \
            "Table-heavy paper should have multiple pages"

        per_page_texts = [p["text"] for p in result["pages"] if p["text"].strip()]
        assert len(per_page_texts) > 1, \
            "Multiple pages should have extracted text"


@pytest.mark.skipif(not HAS_ANY_PDF, reason="No test PDFs available")
class TestRealPDFGeneric:
    """Fallback smoke test using any available PDF."""

    def test_any_pdf_does_not_crash(self, processor):
        """Smoke test: pick the smallest available PDF and process it."""
        pdf = SMALL_PDF if HAS_SMALL_PDF else (
            CRASH_PDF if HAS_CRASH_PDF else (
                TABLE_PDF if HAS_TABLE_PDF else _find_any_pdf()
            )
        )
        assert pdf is not None, "No PDF found for smoke test"

        result = processor.process_pdf(str(pdf))
        validate_output_structure(result, str(pdf))


if __name__ == "__main__":
    pytest.main(["-v", __file__])
