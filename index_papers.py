from src.utils.config import FULL_CONFIG
from src.crawlers.paper_downloader import index_downloaded_papers

print("Phase 4b: Indexing paper chunks...")
count = index_downloaded_papers(config=FULL_CONFIG)
print(f"Done! Indexed {count} paper chunks.")
