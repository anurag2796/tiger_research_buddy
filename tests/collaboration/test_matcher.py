import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.database.models import Idea
from src.collaboration.matcher import IdeaMatcher
from src.database import get_vector_store
from rich.console import Console

console = Console()

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from src.utils.config import CrawlConfig
from src.database.vector_store import VectorStore

def test_collaboration_matcher():
    console.print("\n[bold blue]🧪 Testing Collaboration Matcher...[/]")
    
    # 1. Initialize Vector Store
    temp_dir = tempfile.mkdtemp()
    mock_config = CrawlConfig(
        mode="test",
        max_profiles=1,
        concurrency=1,
        crawl_delay=1,
        paper_limit=1,
        start_urls=[]
    )
    mock_config.CHROMA_DIR = Path(temp_dir)
    store = VectorStore(config=mock_config)
    store.initialize()
    
    # Check if we have any data
    stats = store.get_stats()
    if stats['total_documents'] == 0:
        console.print("[yellow]Vector store is empty. Skipping matcher test.[/]")
        return
        
    # 2. Create a dummy idea
    idea = Idea(
        title="AI for Sustainable Agriculture",
        description="Using deep learning and satellite imagery to optimize crop yields and reduce water usage.",
        author_name="Test Student",
        college="Computing",
        tags=["artificial intelligence", "sustainability", "imaging"]
    )
    
    console.print(f"[bold]created Idea:[/]\nTitle: {idea.title}\nDescription: {idea.description}")
    
    # 3. Run Matching
    with patch("src.collaboration.matcher.get_vector_store", return_value=store):
        matcher = IdeaMatcher()
        console.print("\n[bold]Running Matcher...[/]")
        matches = matcher.match_idea(idea)
    
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 4. Analyze Results
    collabs = matches.get("collaborators", [])
    console.print(f"Found {len(collabs)} potential collaborators.")
    
    for i, match in enumerate(collabs, 1):
        meta = match.get("metadata", {})
        console.print(f"{i}. [green]{meta.get('name')}[/] ({meta.get('college', 'Unknown')}) - {meta.get('doc_type')}")
        # console.print(f"   Similarity: {match.get('distance')}")

if __name__ == "__main__":
    test_collaboration_matcher()
