import sys
from unittest.mock import MagicMock, patch
import pytest
import json

# Mock external dependencies that cause import errors in the restricted environment
MOCK_MODULES = [
    "rich", "rich.console", "rich.progress",
    "fitz", "google.generativeai", "PIL", "dotenv",
    "src.chatbot.ollama_client", "src.chatbot.gemini_client",
    "src.utils.config", "src.utils.db_logger",
    "src.crawlers.vision_crawler", "src.processors.vlm_target_extractor"
]

for module in MOCK_MODULES:
    sys.modules[module] = MagicMock()

# Now import the class under test
from src.processors.pdf_distiller import DeepDistiller

@pytest.fixture
def distiller():
    """Provides a DeepDistiller instance with initialization bypassed."""
    with patch.object(DeepDistiller, '__init__', return_value=None):
        return DeepDistiller()

def test_repair_json_valid(distiller):
    """Test with a perfectly valid JSON string."""
    valid_json = '{"key": "value", "number": 123, "list": [1, 2, 3]}'
    expected = {"key": "value", "number": 123, "list": [1, 2, 3]}
    assert distiller.repair_json(valid_json) == expected

def test_repair_json_with_newlines(distiller):
    """Test with unescaped newlines inside strings, which is a common LLM error."""
    json_with_newlines = '{\n"key": "value with\nnewline",\n"other": "data"\n}'
    # The repair_json implementation replaces all \n with spaces.
    expected = {"key": "value with newline", "other": "data"}
    assert distiller.repair_json(json_with_newlines) == expected

def test_repair_json_with_trailing_commas(distiller):
    """Test with trailing commas in objects and arrays."""
    json_with_trailing_commas = '{"key": "value", "list": [1, 2, 3,],}'
    expected = {"key": "value", "list": [1, 2, 3]}
    assert distiller.repair_json(json_with_trailing_commas) == expected

def test_repair_json_invalid(distiller):
    """Test with completely invalid JSON that cannot be repaired."""
    invalid_json = "This is not JSON at all."
    assert distiller.repair_json(invalid_json) is None
