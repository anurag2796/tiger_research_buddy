from src.database.models import Idea
from src.collaboration.matcher import IdeaMatcher
from src.database import get_vector_store
from rich.console import Console

console = Console()

def test_collaboration_matcher():
    console.print("\n[bold blue]🧪 Testing Collaboration Matcher...[/]")
    
    # 1. Initialize Vector Store
    store = get_vector_store()
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
    matcher = IdeaMatcher()
    console.print("\n[bold]Running Matcher...[/]")
    matches = matcher.match_idea(idea)
    
    # 4. Analyze Results
    collabs = matches.get("collaborators", [])
    console.print(f"Found {len(collabs)} potential collaborators.")
    
    for i, match in enumerate(collabs, 1):
        meta = match.get("metadata", {})
        console.print(f"{i}. [green]{meta.get('name')}[/] ({meta.get('college', 'Unknown')}) - {meta.get('doc_type')}")
        # console.print(f"   Similarity: {match.get('distance')}")

if __name__ == "__main__":
    test_collaboration_matcher()
