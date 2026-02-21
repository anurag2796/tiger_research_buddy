
import asyncio
from dagster import asset, Config, MaterializeResult, MetadataValue
from pathlib import Path
from typing import List

from ..utils.config import get_config, CrawlConfig


from ..crawlers.smart_crawler import SmartCrawler
from ..crawlers.paper_downloader_v3 import download_all_papers
from ..processors.pdf_distiller import DeepDistiller
from ..knowledge_graph.builder import KnowledgeGraphBuilder
from ..database.vector_store import load_data_to_vectorstore, ingest_research_cards

class PipelineConfig(Config):
    mode: str = "restricted"

# 1. Crawl RIT Data
@asset
def rit_data(config: PipelineConfig) -> Path:
    """Crawl RIT websites for faculty and research data."""
    crawl_config = get_config(config.mode)
    
    # Check if data already exists to resume/skip
    if crawl_config.OUTPUT_FILE.exists():
        print(f"Found existing data at {crawl_config.OUTPUT_FILE}. Skipping crawl.")
        return crawl_config.OUTPUT_FILE

    crawler = SmartCrawler(crawl_config)
    
    # Run async crawl
    asyncio.run(crawler.crawl())
    
    return crawl_config.OUTPUT_FILE

# 2. Download PDFs
@asset
def pdfs(config: PipelineConfig, rit_data: Path) -> Path:
    """Download papers mentioned in the crawled data."""
    crawl_config = get_config(config.mode)
    
    # download_all_papers handles its own logic, reading from rit_data
    # We pass rit_data as dependency to ensure ordering
    download_all_papers(crawl_config)
    
    return crawl_config.PDF_DIR

# 3. Distill Papers (Async)
@asset
def research_cards(config: PipelineConfig, pdfs: Path) -> Path:
    """Distill PDFs into structured Research Cards using LLM."""
    crawl_config = get_config(config.mode)
    distiller = DeepDistiller(pdf_dir=crawl_config.PDF_DIR)
    
    # Run async distillation
    asyncio.run(distiller.process_all_async())
    
    cards_dir = crawl_config.BASE_DIR / "research_cards"
    return cards_dir

# 4. Build Knowledge Graph
@asset
def knowledge_graph(config: PipelineConfig, rit_data: Path, research_cards: Path) -> Path:
    """Build KuzuDB knowledge graph from crawled data and research cards."""
    crawl_config = get_config(config.mode)
    
    # Builder reads from config.BASE_DIR/comprehensive_data.json (rit_data) 
    # and research_cards folder.
    
    builder = KnowledgeGraphBuilder(data_dir=crawl_config.BASE_DIR)
    builder.build_from_data(rit_data_file=rit_data)
    
    db_path = crawl_config.BASE_DIR / "kuzu_db"
    return db_path

# 5. Vector Store Ingestion
@asset
def vector_store(config: PipelineConfig, rit_data: Path, research_cards: Path) -> MaterializeResult:
    """Ingest all data into ChromaDB vector store."""
    crawl_config = get_config(config.mode)
    
    # Ingest Profiles
    load_data_to_vectorstore(crawl_config)
    
    # Ingest Research Cards
    ingest_research_cards(crawl_config)
    
    return MaterializeResult(
        metadata={
            "collection_name": crawl_config.COLLECTION_NAME,
            "chroma_dir": str(crawl_config.CHROMA_DIR)
        }
    )
