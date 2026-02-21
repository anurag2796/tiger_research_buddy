import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.crawlers.smart_crawler import SmartCrawler
from src.utils.config import CrawlConfig

# Sample HTML for testing
SAMPLE_HTML = """
<html>
<body>
    <div class="profile">
        <h1>Dr. John Doe</h1>
        <p>Professor of Computer Science</p>
        <p>Email: john.doe@example.com</p>
        <a href="/computing/people/jane_doe">Jane Doe</a>
        <a href="https://google.com">External Link</a>
    </div>
</body>
</html>
"""

# Sample JSON response from LLM
SAMPLE_LLM_RESPONSE = """
```json
{
    "name": "Dr. John Doe",
    "title": "Professor of Computer Science",
    "department": "Computer Science",
    "email": "john.doe@example.com",
    "bio": "Professor of Computer Science",
    "research_interests": ["AI", "ML"],
    "education": ["PhD"],
    "publications": ["Paper A"]
}
```
"""

@pytest.fixture
def mock_config():
    config = MagicMock(spec=CrawlConfig)
    config.START_URLS = ["https://www.rit.edu/computing/"]
    config.CONCURRENCY = 1
    config.CRAWL_DELAY = 0
    config.MAX_PROFILES = 10
    config.CHECKPOINT_FILE = MagicMock()
    config.CHECKPOINT_FILE.exists.return_value = False
    return config

@pytest.mark.asyncio
async def test_extract_links(mock_config):
    crawler = SmartCrawler(config=mock_config)
    links = crawler.extract_links(SAMPLE_HTML, "https://www.rit.edu/computing/")
    
    # Should find the internal link
    assert "https://www.rit.edu/computing/people/jane_doe" in links
    # Should NOT find external link
    assert "https://google.com" not in links

@pytest.mark.asyncio
async def test_extract_profile_data(mock_config):
    crawler = SmartCrawler(config=mock_config)
    
    # Mock LLM Client
    crawler.llm_client.generate = MagicMock(return_value=SAMPLE_LLM_RESPONSE)
    
    data = await crawler.extract_profile_data("https://www.rit.edu/computing/people/john_doe", "Raw Text content")
    
    assert data is not None
    assert data["name"] == "Dr. John Doe"
    assert data["email"] == "john.doe@example.com"
    
    from unittest.mock import ANY
    # Verify num_ctx was passed
    crawler.llm_client.generate.assert_called_with(
        ANY, 
        system_prompt="You are a JSON extractor.", 
        options={"num_ctx": 8192}
    )
