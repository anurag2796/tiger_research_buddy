import unittest
from unittest.mock import MagicMock, patch
from src.crawlers.rit_crawler import RITCrawler

class TestRITCrawler(unittest.TestCase):
    def setUp(self):
        self.crawler = RITCrawler()

    def test_normalize_url(self):
        base = "https://www.rit.edu"
        self.assertEqual(self.crawler._normalize_url("/foo"), f"{base}/foo")
        self.assertEqual(self.crawler._normalize_url("http://example.com"), "http://example.com")
        self.assertEqual(self.crawler._normalize_url("foo"), f"{base}/foo")

    def test_is_research_area_link(self):
        # Valid links
        self.assertTrue(self.crawler._is_research_area_link("/computing/research/artificial-intelligence", "AI"))
        self.assertTrue(self.crawler._is_research_area_link("/research/cybersecurity", "Security"))
        
        # Invalid links
        self.assertFalse(self.crawler._is_research_area_link("/about-us", "About"))
        self.assertFalse(self.crawler._is_research_area_link("#", "Link"))

if __name__ == "__main__":
    unittest.main()
