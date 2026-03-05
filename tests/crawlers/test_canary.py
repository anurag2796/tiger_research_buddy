import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import pytest
import time
from src.chatbot.rag_engine import RAGEngine
from src.database.vector_store import get_vector_store
from src.chatbot.ollama_client import get_ollama_client

# Canary queries - these MUST always work
CANARY_TESTS = [
    {
        "id": 1,
        "query": "Who is Christopher Kanan?",
        "type": "faculty_lookup",
        "must_contain": ["Christopher Kanan", "kanan"],
        "must_not_contain": ["Result 1:", "Context:", "✅ GOOD"],
        "max_time": 10.0,
    },
    {
        "id": 2,
        "query": "Who works on machine learning?",
        "type": "topic_search",
        "must_contain": ["machine learning"],
        "must_not_contain": ["Result 1:", "professor:", "research_area:"],
        "max_time": 10.0,
    },
    {
        "id": 3,
        "query": "What's his email?",
        "type": "follow_up",
        "context_query": "Who is Christopher Kanan?",
        "must_contain": ["@rit.edu"],
        "must_not_contain": ["Result 1", "Result 2", "Context:"],
        "max_time": 10.0,
    },
    {
        "id": 4,
        "query": "What's the weather like today?",
        "type": "off_topic",
        "must_contain": ["research"],
        "must_not_contain": [],
        "max_time": 5.0,
    },
    {
        "id": 5,
        "query": "Who is Professor FakeName?",
        "type": "hallucination_check",
        "must_contain": ["don't have", "not found", "cannot find"],
        "must_not_contain": ["FakeName works", "FakeName is", "FakeName researches"],
        "max_time": 10.0,
    },
]

from pathlib import Path
from src.utils.config import CrawlConfig
from src.database.vector_store import load_data_to_vectorstore
import tempfile
import shutil

@pytest.fixture(scope="module")
def engine():
    """Initialize the RAG engine once for all tests with sample data"""
    # Create Test Config
    test_config = CrawlConfig(
        mode="test",
        max_profiles=1,
        concurrency=1,
        crawl_delay=0,
        paper_limit=1,
        start_urls=[],
    )
    # Override paths to use fixture
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_data.json"
    test_config.OUTPUT_FILE = fixture_path
    test_config.COLLECTION_NAME = "rit_research_test_canary"
    temp_dir = tempfile.mkdtemp()
    test_config.CHROMA_DIR = Path(temp_dir)
    
    # Initialize and Load Data
    # This creates the vector store, clears it, and loads data from fixture
    store = load_data_to_vectorstore(test_config)
    
    ollama_client = get_ollama_client()
    ollama_client.initialize()
    
    rag_engine = RAGEngine(vector_store=store, gemini_client=ollama_client)
    rag_engine.initialize()
    
    yield rag_engine
    
    # Teardown
    if store is not None:
        try:
            store.clear()
        except:
            pass
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.parametrize("test_case", CANARY_TESTS, ids=lambda x: f"{x['type']}")
def test_canary_scenario(engine, test_case):
    """Run a parametrized canary test scenario"""
    
    # Setup context if needed
    if test_case.get("context_query"):
        engine.query(test_case["context_query"])
    else:
        # Clear history for independent tests (unless it's a follow-up)
        # Note: In pytest parametrization, order isn't guaranteed unless we force it.
        # But for this simple case, we assume independence except where context is explicitly set.
        # Ideally, we should clear history before every test that ISN'T a follow-up.
        # Since we use the same engine instance, we should clear it.
        # But wait, how do we distinguish? 
        # Better: Clear history at start, then run context query if needed.
        engine.clear_history()
        if test_case.get("context_query"):
             # Re-run context query to set state
             engine.query(test_case["context_query"])

    start_time = time.time()
    response = engine.query(test_case["query"], n_results=4)
    duration = time.time() - start_time
    
    # 1. Check Response Time
    assert duration <= test_case["max_time"], f"Response took {duration:.2f}s > {test_case['max_time']}s"
    
    response_lower = response.lower()
    
    # 2. Check Required Content
    if test_case.get("type") == "hallucination_check":
        # Special case: Require ANY of the phrases
        match_found = any(req.lower() in response_lower for req in test_case["must_contain"])
        assert match_found, f"Response didn't refuse properly. Expected one of: {test_case['must_contain']}. \nGot: {response}"
    else:
        # Standard case: Require ALL phrases
        for required in test_case.get("must_contain", []):
            assert required.lower() in response_lower, f"Missing required phrase: '{required}'. \nGot: {response}"
            
    # 3. Check Forbidden Content
    for forbidden in test_case.get("must_not_contain", []):
        assert forbidden.lower() not in response_lower, f"Contains forbidden artifact: '{forbidden}'. \nGot: {response}"
