import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import pytest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.document_processor import DocumentProcessor
from src.processors.pdf_distiller import DeepDistiller
from src.database.vector_store import VectorStore
from src.chatbot.rag_engine import RAGEngine
from src.database.database import ResearchDatabase
import json

# Real PDF files for testing
RESTRICTED_PDF_DIR = Path("data/restricted/pdfs")
REAL_PDFS = {
    "small": RESTRICTED_PDF_DIR / "brent_fast_and_accurate_alignment_of_long_bisulfite-seq_reads.pdf",
    "crash": RESTRICTED_PDF_DIR / "connor_language_models_as_emotional_classifiers_for_textual_convers.pdf",
    "heavy": RESTRICTED_PDF_DIR / "pengcheng_hierarchical_semantic_learning_for_multi-class_aorta_segment.pdf"
}

OUTPUT_DIR = Path("tests/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

pytestmark = pytest.mark.integration

@pytest.fixture
def temp_cache_dir():
    """Provides a temporary cache directory for the document processor."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def real_data_docs(temp_cache_dir):
    """Processes real PDFs and yields the DocumentProcessor output."""
    docs = {}
    from src.utils.document_processor import ProcessorConfig
    cfg = ProcessorConfig(cache_dir=str(temp_cache_dir), table_mode="off", pdf_backend="pymupdf")
    with patch("src.utils.document_processor.SURYA_AVAILABLE", False):
        processor = DocumentProcessor(cfg)
    
    # Process only the small one by default to save test time unless others are specifically requested
    if REAL_PDFS["small"].exists():
        docs["small"] = processor.process_pdf(str(REAL_PDFS["small"]))
        
    yield docs

@pytest.fixture
def test_vector_store():
    """Provides an isolated vector store for testing."""
    temp_dir = tempfile.mkdtemp()
    
    from src.utils.config import CrawlConfig
    mock_config = CrawlConfig(
        mode="test",
        max_profiles=1,
        concurrency=1,
        crawl_delay=0,
        paper_limit=1,
        start_urls=[]
    )
    mock_config.CHROMA_DIR = Path(temp_dir)
    mock_config.COLLECTION_NAME = "test_integration_collection"
    
    store = VectorStore(config=mock_config)
    yield store
    # Cleanup vector store files
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def test_db_fixture():
    """Provides an isolated database for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_db_path = Path(temp_dir) / "test_tiger_research.db"
    
    with patch("src.database.database.DB_PATH", temp_db_path):
        db = ResearchDatabase()
        yield db
        
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.skipif(not REAL_PDFS["small"].exists(), reason="Real PDF 'small' not found")
@pytest.mark.asyncio
async def test_deep_distiller_real_data(real_data_docs):
    """
    Test that DeepDistiller can process the output of DocumentProcessor
    on a real PDF and produce a valid ResearchCard.
    """
    assert "small" in real_data_docs, "Small PDF not processed"
    pdf_data = real_data_docs["small"]
    
    # We don't want to actually hit OpenAI/Ollama in every test run unless explicitly enabled
    # But we DO want to verify the pipeline doesn't crash on real data inputs.
    # Therefore, we mock the actual LLM call but let all the data preparation,
    # schema generation, and routing logic run.
    
    distiller = DeepDistiller()
    
    with patch.object(distiller.llm_client, 'generate_async') as mock_llm:
        # Mock a valid JSON response matching the ResearchCard schema
        mock_llm.return_value = '''
        {
          "card_id": "test_id",
          "bibliographic_data": {
              "title": "Spin-Current Noise",
              "authors": [{"name": "M. Jong", "institution": "Leiden"}],
              "year": 1999,
              "primary_domain": "Physics"
          },
          "core_content": {
              "outcomes": ["Finding 1", "Finding 2"]
          },
          "knowledge_graph": {"nodes": []}
        }
        '''
        card = await distiller.distill_async(
            text=pdf_data["content"],
            filename="brent_fast_and_accurate_alignment_of_long_bisulfite-seq_reads.pdf",
            metadata={"source": pdf_data["pdf_path"]}
        )
        
        assert card is not None
        assert isinstance(card, dict)
        assert card["bibliographic_data"]["title"] == "Spin-Current Noise"
        assert card["bibliographic_data"]["primary_domain"] == "Physics"
        assert len(card["core_content"]["outcomes"]) == 2
        
        with open(OUTPUT_DIR / "distilled_research_card.json", "w") as f:
            json.dump(card, f, indent=2)


@pytest.mark.skipif(not REAL_PDFS["crash"].exists(), reason="Real PDF 'crash' not found")
def test_vector_store_indexing_real_data(temp_cache_dir, test_vector_store):
    """
    Test that the VectorStore can index and retrieve data built from
    the PDF that previously crashed the pipeline (due to meta-tensor error).
    """
    # 1. Process the "crash" PDF
    from src.utils.document_processor import ProcessorConfig
    cfg = ProcessorConfig(cache_dir=str(temp_cache_dir), table_mode="off", pdf_backend="pymupdf")
    with patch("src.utils.document_processor.SURYA_AVAILABLE", False):
        processor = DocumentProcessor(cfg)
    pdf_data = processor.process_pdf(str(REAL_PDFS["crash"]))
    
    # Check that we extracted text from it
    assert len(pdf_data["content"]) > 0
    
    # 2. Add it to the vector store
    # We use a subset of the content to prevent massive embedding times in tests
    test_vector_store.add_documents([{
        "id": "crash_pdf_001",
        "content": pdf_data["content"][:1000], # First 1000 chars
        "metadata": {"source": pdf_data["pdf_path"], "type": "test_crash_pdf"}
    }])
    
    # Check that document was added by verifying chromadb count
    assert test_vector_store.collection.count() == 1
    
    # 3. Search the vector store
    results = test_vector_store.search("language models emotional classifiers", n_results=1)
    
    assert len(results) > 0
    assert results[0]["id"] == "crash_pdf_001"
    assert "test_crash_pdf" in results[0]["metadata"]["type"]


@pytest.mark.skipif(not REAL_PDFS["small"].exists(), reason="Real PDF 'small' not found")
def test_query_engine_real_data(temp_cache_dir, test_vector_store, test_db_fixture):
    """
    Test the QueryEngine (RAGEngine) using data extracted from a real PDF.
    """
    # 1. Process PDF and load into vector store
    from src.utils.document_processor import ProcessorConfig
    cfg = ProcessorConfig(cache_dir=str(temp_cache_dir), table_mode="off", pdf_backend="pymupdf")
    with patch("src.utils.document_processor.SURYA_AVAILABLE", False):
        processor = DocumentProcessor(cfg)
    pdf_data = processor.process_pdf(str(REAL_PDFS["small"]))
    
    # Add a specific paragraph so we can search for it
    test_text = "Spin-current noise from fluctuation relations in mesoscopic systems."
    test_vector_store.add_documents([
        {"id": "target_doc", "content": test_text, "metadata": {"source": "test", "is_target": True}},
        {"id": "bg_doc", "content": pdf_data["content"][:500], "metadata": {"source": "pdf", "is_target": False}}
    ])
    
    # 2. Initialize RAGEngine
    engine = RAGEngine(vector_store=test_vector_store)
    engine.initialize()
    
    # We mock the LLM generation part of the QueryEngine to isolate retrieval and prompt building tests
    # from external API dependencies
    with patch.object(engine.gemini_client, 'generate') as mock_generate:
        mock_generate.return_value = "Based on the context, spin-current noise is related to fluctuation relations."
        
        # 3. Perform a query
        response = engine.query("What is spin-current noise?")
        
        # 4. Verify the RAG pipeline behavior
        assert "spin-current noise is related to fluctuation relations" in response
        # Verify the context was correctly retrieved from the vector store
        _, kwargs = mock_generate.call_args
        context_passed = kwargs.get("context", "")
        
        # Ensure our target test_text made it into the retrieved context
        assert test_text in context_passed
        
        # Save RAG query result for manual review
        with open(OUTPUT_DIR / "rag_query_result.txt", "w") as f:
            f.write(f"QUERY: What is spin-current noise?\n\n")
            f.write(f"RESPONSE:\n{response}\n\n")
            f.write(f"RETRIEVED CONTEXT:\n{context_passed}")
