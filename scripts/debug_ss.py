import sys
sys.path.append(".")
from src.crawlers.paper_downloader_v3 import PaperDownloader

def debug_semantic_scholar():
    downloader = PaperDownloader()
    
    # Test with a known RIT professor
    query = "H. B. Acharya" 
    print(f"Querying Semantic Scholar for: {query}")
    
    papers = downloader.search_semantic_scholar(query, limit=5)
    
    print(f"\nFound {len(papers)} papers.")
    for p in papers:
        print(f"\nTitle: {p['title']}")
        print(f"Authors: {p['authors']}")
        print(f"Has RIT Affiliation: {p.get('has_rit_affiliation')}")
        # We can't see the raw API response here easily unless we modify the class, 
        # but we can see if our logic worked.

if __name__ == "__main__":
    debug_semantic_scholar()
