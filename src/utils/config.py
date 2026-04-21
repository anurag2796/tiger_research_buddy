"""Configuration management for TigerResearchBuddy."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Hardware profile — import AFTER dotenv so env overrides are loaded first.
# Circular-import safe: hardware.py has no imports from this module.
from .hardware import HW_PROFILE  # noqa: E402

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

GRAPH_DB_PATH = DATA_DIR / "kuzu_db"

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# CORS — comma-separated origins; defaults to wildcard only if env var unset.
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]

# Crawling Configuration
# RIT Colleges Research Pages
COLLEGE_URLS = {
    "computing": "https://www.rit.edu/computing/key-research-areas",
    # --- TEMPORARILY DISABLED: Only crawling CS department ---
    # "engineering": "https://www.rit.edu/engineering/research",
    # "science": "https://www.rit.edu/science/research",
    # "liberal_arts": "https://www.rit.edu/liberalarts/research",
    # "business": "https://www.rit.edu/business/research",
    # "technology": "https://www.rit.edu/cet/research"
}
CRAWL_DELAY = 1.0  # Default delay

class CrawlConfig:
    """Configuration for the crawler pipeline."""
    def __init__(
        self, 
        mode: str, 
        max_profiles: int, 
        concurrency: int, 
        crawl_delay: float,
        paper_limit: int,
        start_urls: list,
        pdf_max_pages: int = 30
    ):
        self.MODE = mode
        self.MAX_PROFILES = max_profiles
        self.CONCURRENCY = concurrency
        self.CRAWL_DELAY = crawl_delay
        self.PAPER_LIMIT_PER_FACULTY = paper_limit
        self.START_URLS = start_urls
        self.PDF_MAX_PAGES = pdf_max_pages
        
        # PDF Pipeline Configuration — driven by HardwareProfile, not hardcoded.
        self.PDF_ENGINE = HW_PROFILE.pdf_engine   # B5 + X-platform fix
        self.PDF_BACKEND = "pymupdf"    # pymupdf, pypdfium2
        self.TABLE_STRATEGY = "auto"    # auto, off, force
        
        # Paths
        if mode == "restricted":
            self.BASE_DIR = DATA_DIR / "restricted"
        else:
            self.BASE_DIR = DATA_DIR
            
        self.OUTPUT_FILE = self.BASE_DIR / f"rit_data_{mode}.json" if mode == "restricted" else DATA_DIR / "rit_data_v2.json"
        
        # Subdirectories for artifacts
        self.PDF_DIR = self.BASE_DIR / "pdfs"
        self.PAPERS_DIR = self.BASE_DIR / "papers"
        self.PUBLICATIONS_DIR = self.BASE_DIR / "publications"
        self.CHECKPOINT_FILE = self.BASE_DIR / f"crawler_checkpoint_{mode}.json"
        
        # Vector DB
        self.CHROMA_DIR = self.BASE_DIR / "chroma"
        self.COLLECTION_NAME = f"rit_research_{mode}"
        
        # Ensure directories exist
        for d in [self.BASE_DIR, self.PDF_DIR, self.PAPERS_DIR, self.PUBLICATIONS_DIR, self.CHROMA_DIR]:
            d.mkdir(parents=True, exist_ok=True)

# Define configurations
RESTRICTED_CONFIG = CrawlConfig(
    mode="restricted",
    max_profiles=10,
    concurrency=5,
    crawl_delay=1.0,
    paper_limit=10,
    start_urls=["https://www.rit.edu/computing/key-research-areas"],
    pdf_max_pages=20
)

FULL_CONFIG = CrawlConfig(
    mode="full",
    max_profiles=1000,          # Fetch up to 1000 faculty profiles
    concurrency=3,             # Fast processing (but throttled from 10 to avoid 429s)
    crawl_delay=1.0,           # Polite delay between faculty pages
    paper_limit=1000,           # Max papers per faculty member
    start_urls=list(COLLEGE_URLS.values()),
    pdf_max_pages=50
)

def get_config(mode: str = "restricted") -> CrawlConfig:
    """Get configuration based on mode."""
    if mode == "full":
        return FULL_CONFIG
    return RESTRICTED_CONFIG

# Embedding Configuration
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"

# ChromaDB Configuration
COLLECTION_NAME = "rit_research"


class LLMConfig:
    """Centralized configuration for LLM interactions."""
    # Dual Model Strategy
    CHAT_MODEL = "qwen2.5:7b"          # Better instruction/citation compliance than llama3.1:8b, same speed
    PIPELINE_MODEL = "gemma4:26b"      # High-quality structured JSON extraction for offline distillation
    
    MODEL_NAME = CHAT_MODEL    # Default to chat model for general usage
    # Context window is hardware-aware: 16384 on M4 Max, 8192 on Jetson Orin.
    # Override with LLM_CONTEXT_WINDOW env var.
    CONTEXT_WINDOW = HW_PROFILE.context_window  # X1 fix
    TEMPERATURE = 0.2          # Low temp for factual extraction
    TIMEOUT = 120              # Seconds
    
    # Generation options — built from the hardware-aware context window.
    DEFAULT_OPTIONS = {
        "num_ctx": HW_PROFILE.context_window,  # X1 fix
        "temperature": TEMPERATURE,
        "num_predict": -1      # infinite generation
    }


def validate_config():
    """Validate that required configuration is present."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY not set. Please add your API key to .env file.\n"
            "Get your key at: https://aistudio.google.com"
        )
    return True
