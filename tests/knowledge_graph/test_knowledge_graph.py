import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
"""Test the knowledge graph and data mining capabilities."""

from rich.console import Console
from rich.table import Table
from src.knowledge_graph.builder import build_knowledge_graph
from src.knowledge_graph.queries import GraphQueries
from src.knowledge_graph.analytics import GraphAnalytics
from src.knowledge_graph.data_mining import DataMining

console = Console()


def test_graph_queries():
    """Test graph query functionality."""
    console.print("\n[bold cyan]🔍 Testing Graph Queries...[/]\n")
    
    build_knowledge_graph()
    from src.knowledge_graph.graph_store import GraphStore
    from src.utils.config import GRAPH_DB_PATH
    store = GraphStore(GRAPH_DB_PATH)
    queries = GraphQueries(store)
    
    # Test 1: Find faculty
    faculty_id = queries.find_faculty_by_name("Travis Desell")
    if faculty_id:
        console.print(f"✓ Found faculty: {faculty_id}")
        
        # Get expertise
        expertise = queries.get_faculty_expertise(faculty_id)
        if expertise:
            console.print(f"\n[bold]Top Research Areas:[/]")
            table = Table(show_header=True)
            table.add_column("Topic", style="cyan")
            table.add_column("Weight", style="green")
            
            for topic in expertise[:10]:
                table.add_row(topic["topic"], f"{topic['weight']:.2f}")
            
            console.print(table)
        
        # Get papers
        papers = queries.get_faculty_papers(faculty_id)
        console.print(f"\n✓ Found {len(papers)} papers")
        if papers:
            console.print(f"  Recent: {papers[0]['title']}")
    
    # Test 2: Find experts in AI
    console.print("\n[bold]Finding AI experts...[/]")
    experts = queries.find_experts_in_topic("artificial-intelligence", top_k=5)
    if experts:
        table = Table(show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Department", style="dim")
        table.add_column("Expertise", style="green")
        
        for expert in experts:
            table.add_row(
                expert["name"],
                expert.get("department", "")[:40],
                f"{expert['expertise_weight']:.2f}"
            )
        
        console.print(table)


def test_data_mining():
    """Test data mining functionality."""
    console.print("\n\n[bold cyan]📊 Testing Data Mining...[/]\n")
    
    dm = DataMining()
    
    # Test 1: Frequent patterns
    console.print("[bold]Frequent Topic Patterns:[/]")
    patterns = dm.find_frequent_topic_patterns(min_support=0.02)
    if patterns:
        for i, pattern in enumerate(patterns[:10], 1):
            topics_str = " + ".join(pattern["topics"])
            console.print(f"  {i}. {topics_str} (appears in {pattern['count']} papers)")
    else:
        console.print("  [dim]No patterns found with this support threshold[/]")
    
    # Test 2: Association rules
    console.print("\n[bold]Topic Association Rules:[/]")
    rules = dm.find_topic_associations(min_confidence=0.5)
    if rules:
        table = Table(show_header=True)
        table.add_column("If", style="cyan")
        table.add_column("Then", style="green")
        table.add_column("Confidence", style="yellow")
        
        for rule in rules[:5]:
            antecedent = " & ".join(rule["antecedent"])
            consequent = " & ".join(rule["consequent"])
            table.add_row(antecedent, consequent, f"{rule['confidence']:.1%}")
        
        console.print(table)
    else:
        console.print("  [dim]No rules found with this confidence threshold[/]")
    
    # Test 3: Key phrases
    console.print("\n[bold]Top Key Phrases (TF-IDF):[/]")
    phrases = dm.extract_key_phrases(top_k=15)
    if phrases:
        for i, (phrase, score) in enumerate(phrases[:15], 1):
            console.print(f"  {i:2}. {phrase:40} ({score:.4f})")
    
    # Test 4: Topic modeling
    console.print("\n[bold]Discovered Research Themes (LDA):[/]")
    topics = dm.discover_topics_lda(n_topics=5, n_words=7)
    if topics:
        for topic in topics:
            keywords = ", ".join(topic["keywords"])
            console.print(f"  Topic {topic['topic_id'] + 1}: {keywords}")


def main():
    console.print("[bold magenta]🐅 TigerResearchBuddy Knowledge Graph Test[/]\n")
    
    try:
        test_graph_queries()
        test_data_mining()
        
        console.print("\n[bold green]✓ All tests completed successfully![/]")
    
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
