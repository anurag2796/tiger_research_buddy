import threading
import time
import pytest
from unittest.mock import MagicMock, patch
from src.crawlers.paper_downloader import PaperDownloader
import requests

class TestPaperDownloaderCounters:
    """Phase 2: Thread-Safe Counters & Accurate Metrics."""

    def test_concurrent_counter_increments(self):
        """100 threads incrementing downloaded and failed counts must not lose counts due to race conditions."""
        # Initialize downloader (bypass full init to avoid loading models, configs)
        downloader = PaperDownloader.__new__(PaperDownloader)
        downloader._counter_lock = threading.Lock()
        downloader._downloaded_count = 0
        downloader._failed_count = 0

        # Create worker functions
        def worker_success():
            for _ in range(100):
                downloader._inc_downloaded()
                time.sleep(0.0001)

        def worker_fail():
            for _ in range(100):
                downloader._inc_failed()
                time.sleep(0.0001)

        threads = []
        for _ in range(10):
            t_succ = threading.Thread(target=worker_success)
            t_fail = threading.Thread(target=worker_fail)
            threads.extend([t_succ, t_fail])

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert downloader.downloaded_count == 1000, f"Expected 1000 downloaded, got {downloader.downloaded_count}"
        assert downloader.failed_count == 1000, f"Expected 1000 failed, got {downloader.failed_count}"

class TestPaperDownloaderCaching:
    """Phase 4: Interest Query Caching"""

    def test_search_cache_prevents_duplicate_api_calls(self):
        downloader = PaperDownloader.__new__(PaperDownloader)
        downloader._search_cache = {}
        downloader._cache_lock = threading.Lock()
        
        # Mock the actual search API call
        mock_api_call = MagicMock(return_value=[{"title": "AI Paper"}])
        
        # First call should hit the mock API
        result1 = downloader._cached_search("Artificial Intelligence", "arxiv", mock_api_call, max_results=5)
        assert mock_api_call.call_count == 1
        assert result1 == [{"title": "AI Paper"}]
        
        # Second call to the same query should return cached result without calling API
        result2 = downloader._cached_search("Artificial Intelligence", "arxiv", mock_api_call, max_results=5)
        # Call count should STILL be 1
        assert mock_api_call.call_count == 1
        assert result2 == [{"title": "AI Paper"}]
        
        # Different query should cause new API call
        mock_api_call.return_value = [{"title": "ML Paper"}]
        result3 = downloader._cached_search("Machine Learning", "arxiv", mock_api_call, max_results=5)
        assert mock_api_call.call_count == 2
        assert result3 == [{"title": "ML Paper"}]

class TestPaperDownloaderBlacklist:
    """Phase 5: Dead URL Blocklist"""
    
    def test_404_urls_are_blacklisted(self, tmp_path):
        downloader = PaperDownloader.__new__(PaperDownloader)
        downloader._lock = threading.Lock()
        downloader._counter_lock = threading.Lock()
        downloader._failed_count = 0
        downloader._blacklist = set()
        downloader._blacklist_path = tmp_path / "dead_urls.json"
        
        downloader.pdf_dir = tmp_path / "pdfs"
        downloader.pdf_dir.mkdir()
        
        # Mock session that raises 404 HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_error = requests.exceptions.HTTPError("404 Not Found")
        mock_error.response = mock_response
        
        downloader.session = MagicMock()
        downloader.session.get.return_value.raise_for_status.side_effect = mock_error
        
        # Override rate limit to avoid test delay
        downloader._rate_limit = MagicMock()
        
        # Bypass logging and console 
        with patch('src.crawlers.paper_downloader.logger'), \
             patch('src.crawlers.paper_downloader.console'):
             
             # Attempt download
             result = downloader.download_pdf("http://dead.link/paper.pdf", "test_paper")
             
             # Should return None and not retry 3 times (only called once before 404 abort)
             assert result is None
             assert downloader.session.get.call_count == 1
             
             # Should be added to blacklist
             assert "http://dead.link/paper.pdf" in downloader._blacklist
             
             # Second call to same URL should NOT even invoke requests
             downloader.session.get.reset_mock()
             result2 = downloader.download_pdf("http://dead.link/paper.pdf", "test_paper")
             assert result2 is None
             assert downloader.session.get.call_count == 0
