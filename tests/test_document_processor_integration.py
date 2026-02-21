
import unittest
import os
import shutil
from src.utils.document_processor import DocumentProcessor, ProcessorConfig

class TestDocumentProcessorIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = "tests/fixtures"
        cls.cache_dir = "tests/cache_test"
        if os.path.exists(cls.cache_dir):
            shutil.rmtree(cls.cache_dir)
            
    @classmethod
    def tearDownClass(cls):
        # cleanup cache
        if os.path.exists(cls.cache_dir):
            shutil.rmtree(cls.cache_dir)

    def test_digital_pdf(self):
        cfg = ProcessorConfig(cache_dir=self.cache_dir, table_mode="off")
        processor = DocumentProcessor(cfg)
        path = os.path.join(self.fixtures_dir, "digital.pdf")
        
        result = processor.process_pdf(path)
        self.assertEqual(result["doc_pages"], 1)
        self.assertEqual(result["pages"][0]["text_source"], "digital")
        self.assertIn("digital text PDF", result["pages"][0]["text"])

    def test_scanned_pdf(self):
        # processing scanned pdf requires OCR
        # We need to see if surya is available, otherwise it falls back to placeholder
        cfg = ProcessorConfig(cache_dir=self.cache_dir, table_mode="off")
        processor = DocumentProcessor(cfg)
        path = os.path.join(self.fixtures_dir, "scanned.pdf")
        
        result = processor.process_pdf(path)
        self.assertEqual(result["doc_pages"], 1)
        # Should be OCR if digital text is empty
        self.assertEqual(result["pages"][0]["text_source"], "ocr")
        
        # If surya is installed and working, we might get text. 
        # If not, we get placeholder.
        # We just assert it tried OCR.

    def test_table_heuristic(self):
        cfg = ProcessorConfig(cache_dir=self.cache_dir, table_mode="auto")
        processor = DocumentProcessor(cfg)
        
        # Test heuristic method directly
        text_with_table = "Table 1: Financials\nYear Revenue\n2020 1000\n2021 2000"
        self.assertTrue(processor._heuristic_table_check(text_with_table))
        
        text_no_table = "Just some plain text paragraph without any tabular structure."
        self.assertFalse(processor._heuristic_table_check(text_no_table))

    def test_backend_pypdfium2(self):
        # Verify pypdfium2 backend works
        cfg = ProcessorConfig(cache_dir=self.cache_dir, pdf_backend="pypdfium2", table_mode="off")
        processor = DocumentProcessor(cfg)
        path = os.path.join(self.fixtures_dir, "digital.pdf")
        
        result = processor.process_pdf(path)
        self.assertEqual(result["pages"][0]["text_source"], "digital")
        self.assertIn("digital text PDF", result["pages"][0]["text"])

if __name__ == "__main__":
    unittest.main()
