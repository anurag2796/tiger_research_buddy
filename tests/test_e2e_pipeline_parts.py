import sys
import pytest
from pathlib import Path

# Fix python paths for tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.database import ResearchDatabase
from src.utils.db_logger import setup_db_logging
from src.crawlers.scholar_crawler import ScholarCrawler
from src.chatbot.rag_engine import get_rag_engine

# Setup logger for tests
logger = setup_db_logging("PipelineTest")

def test_database_logging_schema():
    """Verify that logging and process_timings tables accept inserts with log_id."""
    db = ResearchDatabase()
    
    # Try inserting a log manually using the new schema
    try:
        log_id = db.log_message(level="INFO", module="test_db", message="Testing log insertion")
        assert log_id > 0, "Log message ID should be returned"
        logger.info("Database log insertion successful")
    except Exception as e:
        pytest.fail(f"Database log insertion failed: {e}")

    # Try inserting a timing record
    try:
        timing_id = db.log_timing(
            operation="test_timing",
            duration=1.23,
            start_time="2024-01-01T00:00:00",
            end_time="2024-01-01T00:00:01"
        )
        assert timing_id > 0, "Log timing ID should be returned"
        logger.info("Database timing insertion successful")
    except Exception as e:
        pytest.fail(f"Database timing insertion failed: {e}")

def test_scholar_crawler_enrichment():
    """Verify scholar crawler handles simple enrichment without crashing."""
    try:
        crawler = ScholarCrawler(max_workers=1)
        # Create a mock faculty list
        mock_faculty = [{"name": "Matt Huenerfauth", "department": "School of Information"}]
        
        # This should execute cleanly even if it fails to find data due to mock limitations
        result = crawler.enrich_faculty_data(mock_faculty)
        
        # Verify result is still a list
        assert isinstance(result, list)
        logger.info("Scholar crawler enrichment test passed")
    except Exception as e:
        pytest.fail(f"Scholar enrichment raised unexpected exception: {e}")

def test_rag_engine_query_fallback():
    """Verify RAG engine handles failing queries gracefully."""
    try:
        engine = get_rag_engine()
        engine.initialize()
        
        # Attempt to query. If LLM clients are not configured correctly,
        # it should log an error and use the fallback mechanism rather than crashing.
        response = engine.query("What are the research areas in computing?")
        assert response is not None
        assert isinstance(response, str)
        logger.info("RAG Engine query test passed")
    except Exception as e:
        pytest.fail(f"RAG Engine raised an unexpected crash: {e}")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
