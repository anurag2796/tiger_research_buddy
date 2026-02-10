"""Configuration management for TigerResearchBuddy."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Crawling Configuration
# Crawling Configuration
# RIT Colleges Research Pages
COLLEGE_URLS = {
    "computing": "https://www.rit.edu/computing/key-research-areas",
    "engineering": "https://www.rit.edu/engineering/research",
    "science": "https://www.rit.edu/science/research",
    "liberal_arts": "https://www.rit.edu/liberalarts/research",
    "business": "https://www.rit.edu/business/research",
    "technology": "https://www.rit.edu/cet/research"
}
CRAWL_DELAY = 1.0  # Reduced slightly for speed, but still polite

# Embedding Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ChromaDB Configuration
COLLECTION_NAME = "rit_research"


def validate_config():
    """Validate that required configuration is present."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY not set. Please add your API key to .env file.\n"
            "Get your key at: https://aistudio.google.com"
        )
    return True
