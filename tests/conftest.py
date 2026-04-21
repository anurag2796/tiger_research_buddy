import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client._initialized = True
    client.model = "test-model"
    client.generate.return_name = "Test response about RIT research."
    client.generate_async = AsyncMock(return_value="Test async response.")
    return client

@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store._initialized = True
    store.search.return_value = [{
        "id": "prof_test",
        "content": "Professor: Test Professor\nDepartment: CS\nResearch: ML",
        "metadata": {"doc_type": "professor", "name": "Test Professor", "email": "test@rit.edu"},
        "distance": 0.1
    }]
    store.get_stats.return_value = {"total_documents": 100, "collection_name": "test"}
    return store
