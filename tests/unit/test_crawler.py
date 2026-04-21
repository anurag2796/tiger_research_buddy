import pytest
from unittest.mock import MagicMock, patch
from src.crawlers.smart_crawler import SmartCrawler
from src.utils.config import CrawlConfig

@pytest.fixture
def mock_config():
    return CrawlConfig(
        mode="test",
        max_profiles=1,
        concurrency=1,
        crawl_delay=1,
        paper_limit=1,
        start_urls=["https://www.rit.edu/computing/key-research-areas"],
        pdf_max_pages=20
    )

def test_crawler_extract_links_filter(mock_config):
    # We need to mock the crawler's internal methods to avoid real network calls
    crawler = SmartCrawler(config=mock_config)

    urls_to_test = [
        "https://www.rit.edu/computing/directory/frbics-fran-broderick",
        "https://www.rit.edu/engineering/research",
        "https://www.rit.edu/science/research",
        "https://www.rit.edu/computing/overview"
    ]

    # We'll mock the extract_links method's dependency, which is the soup processing.
    # Since extract_links is what we want to test, we'll mock its input.
    html_content = "<html><a href='/computing/directory/frbics-fran-broderick'>Link 1</a><a href='/engineering/research'>Link 2</a><a href='/computing/overview'>Link 3</a></html>"

    links = crawler.extract_links(html_content, "https://www.rit.edu/computing/key-research-areas")

    assert "https://www.rit.edu/computing/directory/frbics-fran-broderick" in links
    assert "https://www.rit.edu/computing/overview" in links
    assert "https://www.rit.edu/engineering/research" not in links
