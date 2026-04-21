import pytest
from unittest.mock import MagicMock, patch
from src.crawlers.paper_downloader import PaperDownloader
from src.utils.config import CrawlConfig

@pytest.fixture
def mock_config():
    config = CrawlConfig(
        mode="test",
        max_profiles=1,
        concurrency=1,
        crawl_delay=1,
        paper_limit=1,
        start_urls=["https://www.rit.edu/computing/key-research-areas"]
    )
    return config

@pytest.fixture
def downloader(mock_config):
    with patch('src.crawlers.paper_downloader.VisionCrawler'), \
         patch('src.crawlers.paper_downloader.setup_db_logging', return_value=MagicMock()):
        return PaperDownloader(config=mock_config)

def test_author_match_logic_proper(downloader):
    # Test cases:
    # 1. Exact match
    assert downloader._is_author_match("John Smith", ["John Smith", "Jane Doe"]) is True
    # 2. First Initial match
    assert downloader._is_author_match("J. Smith", ["John Smith"]) is True
    # 3. Mismatch
    assert downloader._is_author_match("James Smith", ["John Smith"]) is False
    # 4. No authors
    assert downloader._is_author_match("John Smith", []) is False
