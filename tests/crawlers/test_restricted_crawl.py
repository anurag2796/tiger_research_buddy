import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import asyncio
import json
import os
import sys
from pathlib import Path
from rich.console import Console # Import Console

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crawlers.smart_crawler import SmartCrawler
from src.utils.config import DATA_DIR
import src.crawlers.smart_crawler

TARGET_FILE = DATA_DIR / "target_urls.json"
TEST_OUTPUT_FILE = DATA_DIR / "rit_data_test.json"
TEST_SCHOLAR_FILE = DATA_DIR / "scholar_data_test.json"

async def _test_restricted_crawl_async():
    print("--- Starting Restricted Crawl Test ---")
    
    # 1. Load targets
    if not TARGET_FILE.exists():
        print(f"Error: {TARGET_FILE} not found. Run scripts/extract_target_urls.py first.")
        return

    with open(TARGET_FILE, "r") as f:
        targets = json.load(f)
        
    target_urls = list(targets.values())
    print(f"Loaded {len(target_urls)} target URLs.")
    
    # Subclass for clean testing
    class TestCrawler(SmartCrawler):
        def __init__(self):
            super().__init__()
            self.console = Console() # Ensure console is available

        async def crawl(self, start_url=None, max_profiles=10):
            # Custom crawl loop that trusts the pre-filled queue
            import aiohttp
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
            
            print(f"Test Crawl: Processing {len(self.queue)} URLs...")
            
            profiles_found = 0
            
            async with aiohttp.ClientSession(headers={"User-Agent": "TigerResearchBuddy/Test"}) as session:
                 # Minimal progress bar
                 with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console
                ) as progress:
                    task = progress.add_task("Crawling...", total=max_profiles)
                    
                    # Process in loop until queue empty or max reached
                    while self.queue and profiles_found < max_profiles:
                        # Process batch
                        batch_size = min(self.concurrency, len(self.queue))
                        batch = []
                        for _ in range(batch_size):
                             if self.queue:
                                 batch.append(self.queue.pop(0))
                        
                        tasks = [self.process_url(session, u, progress, task) for u in batch]
                        await asyncio.gather(*tasks)
                        
                        profiles_found = len(self.scraped_data)
            
            self.save_data_test()

        def save_data_test(self):
            with open(TEST_OUTPUT_FILE, "w") as f:
                json.dump({"faculty": self.scraped_data}, f, indent=2)
            print(f"Saved {len(self.scraped_data)} profiles to {TEST_OUTPUT_FILE}")
            
        def extract_links(self, html, url):
            return [] # No recursion

    test_crawler = TestCrawler()
    test_crawler.queue = target_urls
    test_crawler.visited = set(target_urls)
    
    await test_crawler.crawl(max_profiles=len(target_urls))
    
    # 3. Enrich
    from src.crawlers.scholar_crawler import enrich_with_scholar
    
    print("\nEnriching with Scholar data...")
    if TEST_OUTPUT_FILE.exists():
        with open(TEST_OUTPUT_FILE, "r") as f:
            data = json.load(f)
            
        faculty = data.get("faculty", [])
        if not faculty:
            print("No faculty found to enrich.")
            return

        enriched = enrich_with_scholar(faculty)
        data["faculty"] = enriched
        
        with open(TEST_OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
        # 4. Download
        print("\nDownloading Papers...")
        from src.crawlers.paper_downloader_v3 import PaperDownloader
        downloader = PaperDownloader()
        # Limit to 1 paper per faculty for test speed
        # Ensure we pass the enriched data
        downloader.download_faculty_papers(data, max_per_faculty=1)
        
    else:
        print("Test output file not found, skipping enrichment.")

    print("\n--- Test Finished ---")

def test_restricted_crawl():
    """Wrapper for pytest to run async test."""
    asyncio.run(_test_restricted_crawl_async())

if __name__ == "__main__":
    asyncio.run(_test_restricted_crawl_async())
