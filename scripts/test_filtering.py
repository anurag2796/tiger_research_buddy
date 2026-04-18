import sys
import logging
from src.crawlers.paper_downloader import PaperDownloader

# Setup logging to see prints
logging.basicConfig(level=logging.INFO)

def test_filtering():
    downloader = PaperDownloader()
    
    # Test case that failed: Xumin Liu matching irrelevant papers
    faculty_name = "Xumin Liu"
    print(f"Testing filtering for {faculty_name}...")
    
    # manually stub a paper that should be REJECTED
    bad_paper = {
        "title": "Bad Paper",
        "authors": ["Mugurel Ionut Andreica"],
        "source": "arxiv"
    }
    
    match = downloader._is_author_match(faculty_name, bad_paper["authors"])
    print(f"Match result for {bad_paper['authors']}: {match} (Expected: False)")
    
    # Test case that should ACCEPT
    good_paper = {
        "title": "Good Paper",
        "authors": ["X. Liu", "John Doe"],
        "source": "arxiv"
    }
    match = downloader._is_author_match(faculty_name, good_paper["authors"])
    print(f"Match result for {good_paper['authors']}: {match} (Expected: True)")
    
    # Real Search Test Simulation
    print("\nRunning real search simulation...")
    # Mock search_for_faculty to return a mix of good and bad papers
    
    mixed_papers = [
        {"title": "Good Paper", "authors": ["X. Liu"], "source": "arxiv"},
        {"title": "Topic Paper (Bad)", "authors": ["Mugurel Ionut Andreica"], "source": "arxiv"},
        {"title": "Semantic Scholar Paper", "authors": ["Xumin Liu", "Other"], "source": "semantic_scholar"},
    ]
    
    # We mock search_for_faculty to return this list
    downloader.search_for_faculty = lambda n, i, limit: mixed_papers
    
    # Mock Timer to avoid AttributeError
    class MockTimer:
        def __init__(self, *args, **kwargs): self.duration = 0.1
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    # Patch Timer in the imported module/class context
    import src.crawlers.paper_downloader as pd_module
    pd_module.Timer = MockTimer
    
    from rich.progress import Progress
    with Progress() as progress:
        task = progress.add_task("test")
        prof = {"name": faculty_name, "research_interests": ["Data Management"]}
        
        # We need to override download_pdf to avoid actual download
        downloader.download_pdf = lambda url, fn: Path("fake.pdf") 
        downloader.extract_text = lambda path: "text"
        downloader.save_paper_metadata = lambda p, t: None # Mock
        
        results, count = downloader._process_faculty_member(prof, 5, progress, task)
        
        print(f"\nProcessed: {count} valid candidates found (after filter), {len(results)} accepted.")
        for p in results:
            print(f"Accepted: {p['title']} - Authors: {p['authors']}")
            if "Mugurel" in str(p['authors']):
                 print("❌ FAILURE: Bad paper accepted!")
            else:
                 print("✅ SUCCESS: Good paper accepted.")

if __name__ == "__main__":
    test_filtering()
