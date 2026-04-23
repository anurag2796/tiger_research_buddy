from src.utils.config import FULL_CONFIG
from src.database.vector_store import load_data_to_vectorstore, ingest_research_cards
from src.crawlers.paper_downloader import index_downloaded_papers

print("Phase 4a: Indexing faculty profiles...")
load_data_to_vectorstore(FULL_CONFIG)

print("Phase 4b: Indexing paper chunks...")
index_downloaded_papers(config=FULL_CONFIG)

print("Phase 4c: Indexing research cards...")
ingest_research_cards(config=FULL_CONFIG)

print("Done!")
