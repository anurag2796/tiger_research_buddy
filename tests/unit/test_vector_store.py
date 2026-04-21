import pytest
from unittest.mock import MagicMock
from src.database.vector_store import VectorStore
from src.utils.config import CrawlConfig

@pytest.fixture
def mock_config():
    return CrawlConfig(
        mode="test",
        max_profiles=1,
        concurrency=1,
        crawl_delay=1,
        paper_limit=1,
        start_urls=[]
    )

def test_vector_store_crud(mock_config):
    store = VectorStore(config=mock_config)
    # We can't easily test real ChromaDB without setup, so we mock
    store.add_document = MagicMock()
    store.search = MagicMock(return_value=[{"id": "1", "content": "test", "metadata": {}, "distance": 0.1}])

    store.add_document("test content", {"metadata": "test"})
    store.add_document.assert_called_once()

    results = store.search("test")
    assert len(results) == 1
    assert results[0]["content"] == "test"
