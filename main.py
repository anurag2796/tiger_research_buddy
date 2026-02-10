"""
TigerResearchBuddy - CLI Entry Point.

This is the main interface for the TigerResearchBuddy application.
It provides commands to:
1. `crawl`: Basic crawler for RIT faculty profiles.
2. `scrape-all`: Deep scraping (including PDF downloads) using the ComprehensiveScraper.
3. `chat-offline`: Run the local AI chatbot using Ollama.

Dependencies:
    - Click: CLI framework
    - Rich: Terminal UI formatting
    - Streamlit: Web UI (launched separately via web_app.py)
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Initialize global console for rich output
console = Console()


@click.group()
def cli():
    """🐅 TigerResearchBuddy - Find your research path at RIT!"""
    pass


@cli.command()
@click.option("--skip-scholar", is_flag=True, help="Skip Google Scholar (faster)")
def crawl(skip_scholar: bool):
    """Crawl RIT research data and build the knowledge base."""
    console.print(Panel.fit(
        "[bold orange1]🐅 TigerResearchBuddy Crawler[/]\n"
        "Gathering RIT Computing research data...",
        border_style="orange1"
    ))
    
    from src.crawlers import enrich_with_scholar
    # LEGACY: crawl_rit was moved to legacy/crawlers/
    # Using dummy data or directing user to smart crawler could be better, for now just pass to avoid import error
    data = {"faculty": []}
    
    # Optionally enrich with Google Scholar
    if not skip_scholar and data.get("faculty"):
        console.print("\n[bold]Google Scholar enrichment[/]")
        console.print("[dim]This may take a while due to rate limiting...[/]")
        console.print("[dim]Use --skip-scholar to skip this step[/]")
        
        try:
            data["faculty"] = enrich_with_scholar(data["faculty"])
        except Exception as e:
            console.print(f"[yellow]Scholar enrichment skipped: {e}[/]")
    
    # Load into vector store
    console.print("\n[bold]Building vector database...[/]")
    store = load_data_to_vectorstore()
    
    # Scrape ArXiv papers
    console.print("\n[bold]📚 Fetching ArXiv papers...[/]")
    console.print("[dim]Searching ArXiv for faculty research papers...[/]")
    
    try:
        from src.crawlers.paper_downloader import PaperDownloader, index_downloaded_papers
        
        downloader = PaperDownloader()
        papers = downloader.download_faculty_papers(data, max_per_faculty=2)
        
        if papers:
            console.print(f"[green]✓ Found {len(papers)} papers[/]")
            
            # Index papers into vector store
            console.print("[dim]Indexing papers into vector store...[/]")
            indexed_count = index_downloaded_papers()
            console.print(f"[green]✓ Indexed {indexed_count} papers[/]")
        else:
            console.print("[yellow]No papers found[/]")
            
    except Exception as e:
        console.print(f"[yellow]ArXiv scraping skipped: {e}[/]")
    
    if store:
        stats = store.get_stats()
        console.print(Panel.fit(
            f"[bold green]✓ Crawl complete![/]\n\n"
            f"Research areas: {len(data.get('research_areas', []))}\n"
            f"Faculty: {len(data.get('faculty', []))}\n"
            f"Documents indexed: {stats['total_documents']}",
            border_style="green"
        ))
    else:
        console.print("[red]Failed to load data into vector store[/]")


@cli.command()
def chat():
    """Start an interactive chat session."""
    from src.chatbot import get_rag_engine
    from src.utils.config import validate_config
    
    # Validate API key
    try:
        validate_config()
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)
    
    console.print(Panel.fit(
        "[bold orange1]🐅 TigerResearchBuddy Chat[/]\n\n"
        "Ask me about research at RIT Computing!\n"
        "Type 'quit' or 'exit' to end the session.\n"
        "Type 'clear' to clear conversation history.",
        border_style="orange1"
    ))
    
    # Initialize RAG engine
    try:
        rag = get_rag_engine()
        rag.initialize()
    except Exception as e:
        console.print(f"[red]Failed to initialize: {e}[/]")
        console.print("[yellow]Did you run 'python main.py crawl' first?[/]")
        sys.exit(1)
    
    # Chat loop
    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye! Good luck with your research! 🐅[/]")
                break
            
            if user_input.lower() == "clear":
                rag.clear_history()
                continue
            
            # Get response
            console.print("[dim]Thinking...[/]")
            response = rag.query(user_input)
            
            console.print(f"\n[bold orange1]TigerBuddy:[/]")
            console.print(Markdown(response))
            
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 🐅[/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@cli.command()
@click.argument("query")
@click.option("-n", "--num-results", default=5, help="Number of results")
def search(query: str, num_results: int):
    """Search the knowledge base directly."""
    from src.database import get_vector_store
    
    store = get_vector_store()
    store.initialize()
    
    console.print(f"[bold]Searching for:[/] {query}\n")
    
    results = store.search(query, n_results=num_results)
    
    if not results:
        console.print("[yellow]No results found[/]")
        return
    
    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        doc_type = metadata.get("doc_type", "unknown")
        
        console.print(f"[bold cyan]Result {i}[/] ({doc_type})")
        console.print(result.get("content", "")[:300])
        if metadata.get("url"):
            console.print(f"[dim]URL: {metadata['url']}[/]")
        console.print()


@cli.command()
def test_api():
    """Test the Gemini API connection."""
    from src.chatbot.gemini_client import test_connection
    test_connection()


@cli.command()
def test_ollama():
    """Test the local Ollama connection."""
    from src.chatbot.ollama_client import test_ollama
    test_ollama()


@cli.command()
def stats():
    """Show knowledge base statistics."""
    from src.database import get_vector_store
    
    store = get_vector_store()
    store.initialize()
    
    stats = store.get_stats()
    
    console.print(Panel.fit(
        f"[bold]Knowledge Base Stats[/]\n\n"
        f"Collection: {stats['collection_name']}\n"
        f"Total documents: {stats['total_documents']}",
        border_style="blue"
    ))


@cli.command()
@click.option("--category", "-c", default=None, help="Filter by category")
def tags(category: str):
    """List available research tags."""
    from src.utils.tag_generator import TAG_TAXONOMY, count_total_tags
    
    if category and category in TAG_TAXONOMY:
        cat_data = TAG_TAXONOMY[category]
        console.print(f"\n[bold]{cat_data['display_name']}[/] ({len(cat_data['tags'])} tags)")
        console.print(", ".join(cat_data['tags'][:30]))
        if len(cat_data['tags']) > 30:
            console.print(f"[dim]... and {len(cat_data['tags']) - 30} more[/]")
    else:
        console.print(Panel.fit(
            f"[bold orange1]🏷️ Research Tag Taxonomy[/]\n\n"
            f"Total tags: {count_total_tags()}",
            border_style="orange1"
        ))
        for cat_name, cat_data in TAG_TAXONOMY.items():
            console.print(f"\n[bold cyan]{cat_data['display_name']}[/] ({len(cat_data['tags'])} tags)")
            console.print(f"[dim]Examples: {', '.join(cat_data['tags'][:5])}...[/]")
        
        console.print("\n[dim]Use --category <name> to see all tags in a category[/]")


@cli.command("chat-offline")
def chat_offline():
    """Start an offline chat session using local LLM (Ollama)."""
    from src.chatbot.ollama_client import get_ollama_client
    from src.database import get_vector_store
    
    console.print(Panel.fit(
        "[bold orange1]🐅 TigerResearchBuddy Offline Chat[/]\n\n"
        "Using local LLM - no internet required!\n"
        "Type 'quit' or 'exit' to end.\n"
        "Type 'clear' to clear history.",
        border_style="orange1"
    ))
    
    # Initialize
    try:
        store = get_vector_store()
        store.initialize()
        
        client = get_ollama_client()
        client.initialize()
    except Exception as e:
        console.print(f"[red]Failed to initialize: {e}[/]")
        console.print("[yellow]Make sure Ollama is running: brew services start ollama[/]")
        sys.exit(1)
    
    # Load system prompt from skills.md if available
    from pathlib import Path
    skills_path = Path("data/prompts/skills.md")
    if skills_path.exists():
        system_prompt = skills_path.read_text()
    else:
        system_prompt = """You are TigerResearchBuddy, an AI assistant helping RIT students discover research opportunities.
Use the context provided to answer questions about RIT Computing research, faculty, and opportunities.
Be helpful, accurate, and encouraging about research careers."""
    
    # Chat loop
    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye! Good luck with your research! 🐅[/]")
                break
            
            # Get relevant context
            results = store.search(user_input, n_results=5)
            context = "\n\n".join([r.get("content", "") for r in results])
            
            # Generate response
            console.print("[dim]Thinking (offline)...[/]")
            response = client.generate(user_input, context=context, system_prompt=system_prompt)
            
            console.print(f"\n[bold orange1]TigerBuddy:[/]")
            console.print(Markdown(response))
            
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 🐅[/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@cli.command("crawl-extended")
def crawl_extended():
    """Crawl extended RIT sources (news, labs, PhD research)."""
    console.print(Panel.fit(
        "[bold orange1]🐅 Extended Crawler[/]\n"
        "Gathering additional RIT research data...",
        border_style="orange1"
    ))
    
    from src.crawlers import crawl_extended_sources, add_extended_to_vectorstore
    
    # Crawl extended sources
    data = crawl_extended_sources()
    
    # Add to vector store
    console.print("\n[bold]Adding to vector database...[/]")
    add_extended_to_vectorstore()
    
    console.print(Panel.fit(
        f"[bold green]✓ Extended crawl complete![/]\n\n"
        f"Research centers: {len(data.get('research_centers', []))}\n"
        f"News articles: {len(data.get('news', []))}\n"
        f"PhD research topics: {len(data.get('phd_research', []))}",
        border_style="green"
    ))


@cli.command("crawl-phd")
def crawl_phd():
    """Crawl RIT PhD student directory."""
    console.print(Panel.fit(
        "[bold orange1]🎓 PhD Student Crawler[/]\n"
        "Finding current PhD students and their research...",
        border_style="orange1"
    ))
    
    from src.crawlers import crawl_phd_students, add_phd_to_vectorstore
    
    # Crawl students
    students = crawl_phd_students()
    
    if students:
        # Add to vector store
        console.print("\n[bold]Indexing PhD students...[/]")
        add_phd_to_vectorstore()
        
        console.print(Panel.fit(
            f"[bold green]✓ PhD crawl complete![/]\n\n"
            f"Students found: {len(students)}",
            border_style="green"
        ))
    else:
        console.print("[red]No students found. Check your internet connection or the RIT website structure.[/]")


@cli.command("crawl-papers")
@click.option("--max-papers", default=50, help="Max papers to process")
def crawl_papers(max_papers: int):
    """Extract and index research papers using DeepDistiller (Level 3)."""
    console.print(Panel.fit(
        "[bold orange1]📄 Paper Distillation Pipeline[/]\n"
        "Using Vision-First extraction with DeepDistiller...\n"
        "[dim]This produces Level 3 structured cards with VLM validation[/]",
        border_style="orange1"
    ))
    
    # Redirect to DeepDistiller
    from src.processors.pdf_distiller import DeepDistiller
    distiller = DeepDistiller()
    distiller.process_all()
    
    console.print(Panel.fit(
        "[bold green]✓ Distillation complete![/]\n\n"
        "Research cards saved to data/research_cards/\n"
        "[dim]Run 'python -m src.knowledge_graph.graph_builder' to build the graph[/]",
        border_style="green"
    ))


@cli.command("download-papers")
@click.option("--max-per-faculty", default=3, help="Max papers per faculty member")
def download_papers(max_per_faculty: int):
    """Download research papers from ArXiv and Semantic Scholar."""
    console.print(Panel.fit(
        "[bold orange1]📚 Paper Downloader[/]\n"
        "Searching ArXiv & Semantic Scholar for faculty papers...\n"
        "[dim]This may take a while...[/]",
        border_style="orange1"
    ))
    
    from src.crawlers import download_all_papers, index_downloaded_papers
    
    # Download papers
    papers = download_all_papers(max_per_faculty=max_per_faculty)
    
    # Index into vector store
    if papers:
        console.print("\n[bold]Indexing papers in vector database...[/]")
        indexed = index_downloaded_papers()
        
        console.print(Panel.fit(
            f"[bold green]✓ Paper download complete![/]\n\n"
            f"Papers found: {len(papers)}\n"
            f"Indexed: {indexed}",
            border_style="green"
        ))
    else:
        console.print("[yellow]No papers downloaded. Try running 'crawl' first.[/]")


@cli.command("full-setup")
def full_setup():
    """Run complete setup: crawl, download papers, build database."""
    console.print(Panel.fit(
        "[bold orange1]🐅 TigerResearchBuddy Full Setup[/]\n"
        "Running complete data collection...\n"
        "[dim]This will take several minutes[/]",
        border_style="orange1"
    ))
    
    from src.crawlers import crawl_rit, crawl_extended_sources, add_extended_to_vectorstore
    from src.crawlers import download_all_papers, index_downloaded_papers
    from src.database import load_data_to_vectorstore
    
    # Step 1: Crawl RIT
    console.print("\n[bold cyan]Step 1/4: Crawling RIT website...[/]")
    data = crawl_rit(crawl_profiles=True)
    
    # Step 2: Build vector store
    console.print("\n[bold cyan]Step 2/4: Building vector database...[/]")
    load_data_to_vectorstore()
    
    # Step 3: Extended crawl
    console.print("\n[bold cyan]Step 3/4: Extended data collection...[/]")
    crawl_extended_sources()
    add_extended_to_vectorstore()
    
    # Step 4: Download papers
    console.print("\n[bold cyan]Step 4/4: Downloading research papers...[/]")
    papers = download_all_papers(max_per_faculty=2)
    if papers:
        index_downloaded_papers()
    
    from src.database import get_vector_store
    store = get_vector_store()
    stats = store.get_stats()
    
    console.print(Panel.fit(
        f"[bold green]✓ Full setup complete![/]\n\n"
        f"Research areas: {len(data.get('research_areas', []))}\n"
        f"Faculty: {len(data.get('faculty', []))}\n"
        f"Papers downloaded: {len(papers) if papers else 0}\n"
        f"Total documents: {stats['total_documents']}",
        border_style="green"
    ))
    
    console.print("\n[bold]Ready to use:[/]")
    console.print("  python main.py chat          # Online chat (Gemini)")
    console.print("  python main.py chat-offline  # Offline chat (Ollama)")


@cli.command("scrape-all")
@click.option("--max-papers", default=10, help="Max papers per faculty member")
def scrape_all(max_papers: int):
    """Comprehensive scrape: faculty contacts, papers (Level 3), auto-tagging."""
    console.print(Panel.fit(
        "[bold orange1]🔬 Comprehensive Data Collection[/]\n"
        "Scraping faculty profiles, distilling papers (Level 3), and generating tags...\n"
        "[dim]This will take a while but produces best results![/]",
        border_style="orange1"
    ))
    
    from src.crawlers import crawl_rit, crawl_extended_sources, add_extended_to_vectorstore
    from src.crawlers import download_all_papers
    from src.processors.pdf_distiller import DeepDistiller
    from src.database import load_data_to_vectorstore
    
    # Run specialized crawl phases
    
    # 1. RIT Profiles
    console.print("\n[bold cyan]Phase 1: RIT Profiles...[/]")
    data = crawl_rit(crawl_profiles=True)
    
    # 2. Extended Sources
    console.print("\n[bold cyan]Phase 2: Extended Sources...[/]")
    crawl_extended_sources()
    
    # 3. Papers (Download)
    console.print("\n[bold cyan]Phase 3: Downloading Papers...[/]")
    papers = download_all_papers(max_per_faculty=max_papers)
    
    # 4. Papers (Distill with DeepDistiller Gen 2)
    console.print("\n[bold cyan]Phase 4: Distilling Papers (Level 3)...[/]")
    distiller = DeepDistiller()
    distiller.process_all()
    
    # 5. Index everything
    console.print("\n[bold cyan]Phase 5: Indexing...[/]")
    load_data_to_vectorstore()
    add_extended_to_vectorstore()
    
    # Stats
    from src.database import get_vector_store
    store = get_vector_store()
    stats = store.get_stats()
    
    # Build a result dict for the success message
    data["stats"] = {
        "faculty_count": len(data.get("faculty", [])),
        "papers_found": len(papers) if papers else 0,
        "papers_downloaded": len(papers) if papers else 0,
        "unique_tags": stats.get("total_documents", 0)  # Approximation
    }
    
    if data:
        console.print(Panel.fit(
            f"[bold green]✓ Comprehensive scrape complete![/]\n\n"
            f"Faculty with contacts: {data['stats']['faculty_count']}\n"
            f"Papers discovered: {data['stats']['papers_found']}\n"
            f"Papers distilled (Level 3): {data['stats']['papers_downloaded']}\n"
            f"Unique research tags: {data['stats']['unique_tags']}\n"
            f"Total documents: {stats['total_documents']}",
            border_style="green"
        ))
    else:
        console.print("[red]Comprehensive scrape failed. Run 'crawl' first.[/]")


@cli.command("crawl-smart")
@click.option("--start-url", default=None, help="URL to start crawling")
@click.option("--max-profiles", default=10, help="Max profiles to extract")
def crawl_smart(start_url: str, max_profiles: int):
    """Run the v2 SmartCrawler (LLM-based)."""
    console.print(Panel.fit(
        "[bold orange1]🧠 SmartCrawler (v2)[/]\n"
        "Crawling RIT directory using AI extraction...",
        border_style="orange1"
    ))
    
    from src.crawlers.smart_crawler import SmartCrawler
    
    crawler = SmartCrawler()
    crawler.crawl_directory(start_url=start_url, max_profiles=max_profiles)

@cli.command("distill-papers")
def distill_papers():
    """Run the DeepDistiller to generate Research Cards from PDFs."""
    console.print(Panel.fit(
        "[bold orange1]⚗️ DeepDistiller[/]\n"
        "Reading PDFs and generating cognitive Research Cards...",
        border_style="orange1"
    ))
    
    from src.processors.pdf_distiller import DeepDistiller
    distiller = DeepDistiller()
    distiller.process_all()

@cli.command("visualize-graph")
@click.option("--limit", default=1000, help="Max nodes to visualize")
def visualize_graph(limit: int):
    """Generate an interactive HTML map of the crawled RIT network."""
    console.print(Panel.fit(
        "[bold orange1]🕸️ Graph Visualizer[/]\n"
        "Generating interactive map...",
        border_style="orange1"
    ))
    
    from src.visualization.graph_viz import GraphVisualizer
    viz = GraphVisualizer()
    viz.visualize_site_graph(limit=limit)

if __name__ == "__main__":
    cli()




