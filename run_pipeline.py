#!/usr/bin/env python3
"""
TigerResearchBuddy — End-to-End Pipeline Runner
================================================
Runs all stages needed to go from a blank slate to a fully working app.

Usage:
    python run_pipeline.py                        # Restricted mode (default)
    python run_pipeline.py --mode full            # Full CS department
    python run_pipeline.py --skip-crawl           # Skip stage 1 (already done)
    python run_pipeline.py --skip-crawl --skip-scholar --skip-download  # Resume from distill

Stages:
    1  Crawl       — Harvest faculty profiles from RIT CS site
    2  Scholar     — Enrich with Google Scholar metrics
    3  Download    — Pull PDFs from ArXiv & Semantic Scholar
    4  Distill     — AI reads PDFs → structured Research Cards
    5  Index       — Embed all data into vector store (Chroma)
    6  Graph       — Build knowledge graph (optional, needs Ollama)
"""

import sys
import time
import json
import argparse
import traceback
from pathlib import Path
from datetime import timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

console = Console()


# ─── Faculty Deduplication ────────────────────────────────────────────────────

def deduplicate_faculty(faculty: list[dict]) -> list[dict]:
    """Merge duplicate faculty entries by name, combining list fields.

    The crawler stores one entry per (faculty, research_area_page), so faculty
    appearing on multiple pages get duplicated.  This merges them into a single
    entry per unique name, unioning research_interests, publications, etc.
    """
    merged: dict[str, dict] = {}   # key = lowercase name

    # Fields whose values should be merged (union of lists)
    LIST_FIELDS = [
        "research_interests", "research_areas", "publications",
        "courses", "education", "awards", "links",
    ]

    for entry in faculty:
        name = entry.get("name", "").strip()
        if not name:
            continue
        key = name.lower()

        if key not in merged:
            # First occurrence — deep-copy to avoid mutation
            merged[key] = {k: (list(v) if isinstance(v, list) else v)
                           for k, v in entry.items()}
        else:
            # Merge list fields via order-preserving union
            existing = merged[key]
            for field in LIST_FIELDS:
                old_vals = existing.get(field, [])
                new_vals = entry.get(field, [])
                if isinstance(old_vals, list) and isinstance(new_vals, list):
                    seen = {str(v).lower() for v in old_vals}
                    for v in new_vals:
                        if str(v).lower() not in seen:
                            old_vals.append(v)
                            seen.add(str(v).lower())
                    existing[field] = old_vals
            # Keep the longer bio / description
            for text_field in ["bio", "description", "title"]:
                old_txt = existing.get(text_field, "") or ""
                new_txt = entry.get(text_field, "") or ""
                if len(new_txt) > len(old_txt):
                    existing[text_field] = new_txt

    result = list(merged.values())
    return result

# ─── Stage result tracking ───────────────────────────────────────────────────

class StageResult:
    def __init__(self, name: str):
        self.name = name
        self.status = "skipped"   # skipped | done | failed
        self.detail = ""
        self.elapsed = 0.0

    def mark_done(self, detail: str = "", elapsed: float = 0.0):
        self.status = "done"
        self.detail = detail
        self.elapsed = elapsed

    def mark_failed(self, error: str, elapsed: float = 0.0):
        self.status = "failed"
        self.detail = error
        self.elapsed = elapsed

    def mark_skipped(self, reason: str = ""):
        self.status = "skipped"
        self.detail = reason


# ─── Banner helpers ───────────────────────────────────────────────────────────

def stage_banner(n: int, title: str):
    console.print()
    console.print(Rule(f"[bold orange1]Stage {n}: {title}[/]", style="orange1"))


def success(msg: str):
    console.print(f"[bold green]  ✓ {msg}[/]")


def warn(msg: str):
    console.print(f"[yellow]  ⚠ {msg}[/]")


def fail(msg: str):
    console.print(f"[bold red]  ✗ {msg}[/]")


# ─── Summary table ────────────────────────────────────────────────────────────

def print_summary(results: list[StageResult]):
    console.print()
    table = Table(
        title="🐅 Pipeline Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold orange1",
        border_style="orange1"
    )
    table.add_column("Stage", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Time")
    table.add_column("Detail", no_wrap=False)

    icons = {"done": "[bold green]✓ Done[/]", "failed": "[bold red]✗ Failed[/]", "skipped": "[dim]— Skipped[/]"}

    for r in results:
        elapsed_str = str(timedelta(seconds=int(r.elapsed))) if r.elapsed > 0 else "—"
        table.add_row(r.name, icons.get(r.status, r.status), elapsed_str, r.detail[:80])

    console.print(table)
    any_failed = any(r.status == "failed" for r in results)
    if any_failed:
        console.print("\n[red]Pipeline completed with errors. Check above for details.[/]")
        sys.exit(1)
    else:
        console.print("\n[bold green]✅ Pipeline complete! Launch the app:[/]")
        console.print("   [bold cyan]streamlit run web_app.py[/]")


# ─── Stage 1: Crawl ──────────────────────────────────────────────────────────

def stage_crawl(config, result: StageResult) -> dict:
    """Crawl RIT CS faculty profiles with SmartCrawler."""
    from src.crawlers.smart_crawler import run_smart_crawl
    t0 = time.perf_counter()
    try:
        faculty = run_smart_crawl(max_profiles=config.MAX_PROFILES)
        data = {"faculty": faculty}
        # Save raw crawl output
        with open(config.OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)
        elapsed = time.perf_counter() - t0
        n = len(faculty)
        success(f"{n} faculty profiles crawled → {config.OUTPUT_FILE.name}")
        result.mark_done(f"{n} profiles", elapsed)
        return data
    except Exception as e:
        elapsed = time.perf_counter() - t0
        fail(f"Crawl failed: {e}")
        result.mark_failed(str(e)[:80], elapsed)
        return {}


# ─── Stage 2: Scholar Enrichment ─────────────────────────────────────────────

def stage_scholar(config, data: dict, result: StageResult) -> dict:
    """Enrich faculty profiles with Google Scholar metrics."""
    from src.crawlers.scholar_crawler import enrich_with_scholar
    t0 = time.perf_counter()
    faculty = data.get("faculty", [])
    if not faculty:
        warn("No faculty data to enrich — loading from disk")
        try:
            with open(config.OUTPUT_FILE) as f:
                data = json.load(f)
            faculty = data.get("faculty", [])
        except Exception as e:
            result.mark_failed(f"Could not load data: {e}")
            return data

    try:
        data["faculty"] = enrich_with_scholar(faculty)
        with open(config.OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)
        elapsed = time.perf_counter() - t0
        enriched = sum(1 for f in data["faculty"] if f.get("scholar"))
        success(f"{enriched}/{len(faculty)} faculty enriched with Scholar data")
        result.mark_done(f"{enriched} enriched", elapsed)
        return data
    except Exception as e:
        elapsed = time.perf_counter() - t0
        fail(f"Scholar enrichment failed: {e}")
        result.mark_failed(str(e)[:80], elapsed)
        return data


# ─── Stage 3: Download Papers ─────────────────────────────────────────────────

def stage_download(config, data: dict, result: StageResult) -> list:
    """Download PDFs from ArXiv & Semantic Scholar."""
    from src.crawlers.paper_downloader_v3 import PaperDownloader
    t0 = time.perf_counter()

    # Load data from disk if not provided
    if not data.get("faculty"):
        try:
            with open(config.OUTPUT_FILE) as f:
                data = json.load(f)
        except Exception as e:
            result.mark_failed(f"Could not load data: {e}")
            return []

    try:
        downloader = PaperDownloader(config)
        papers = downloader.download_faculty_papers(
            data,
            max_per_faculty=config.PAPER_LIMIT_PER_FACULTY
        )
        elapsed = time.perf_counter() - t0
        n = len(papers)
        success(f"{n} papers downloaded → {config.PDF_DIR}")
        result.mark_done(f"{n} papers", elapsed)
        return papers
    except Exception as e:
        elapsed = time.perf_counter() - t0
        fail(f"Download failed: {e}")
        traceback.print_exc()
        result.mark_failed(str(e)[:80], elapsed)
        return []


# ─── Stage 4: Distill Papers ──────────────────────────────────────────────────

def stage_distill(config, result: StageResult):
    """Run DeepDistiller to produce Research Cards from PDFs."""
    from src.processors.pdf_distiller import DeepDistiller
    t0 = time.perf_counter()

    pdf_dir = config.PDF_DIR
    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        warn(f"No PDFs found in {pdf_dir} — skipping distillation")
        result.mark_skipped("No PDFs found")
        return

    try:
        cards_dir = config.BASE_DIR / "research_cards"
        distiller = DeepDistiller(
            pdf_dir=pdf_dir,
            faculty_db_path=config.OUTPUT_FILE,
            output_dir=cards_dir,
            max_pages=config.PDF_MAX_PAGES
        )
        distiller.process_all()
        elapsed = time.perf_counter() - t0

        n_cards = len(list(cards_dir.glob("*.json"))) if cards_dir.exists() else 0
        success(f"{n_cards} Research Cards distilled → {cards_dir}/")
        result.mark_done(f"{n_cards} cards", elapsed)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        fail(f"Distillation failed: {e}")
        traceback.print_exc()
        result.mark_failed(str(e)[:80], elapsed)


# ─── Stage 5: Index into Vector Store ────────────────────────────────────────

def stage_index(config, result: StageResult):
    """Load crawled data and Research Cards into ChromaDB."""
    from src.database.vector_store import load_data_to_vectorstore, ingest_research_cards
    t0 = time.perf_counter()

    doc_count = 0
    try:
        import filelock
        lock_path = config.BASE_DIR / ".pipeline.lock"
        with filelock.FileLock(lock_path):
            # 5a. Ingest faculty/research-area profiles
            if config.OUTPUT_FILE.exists():
                store = load_data_to_vectorstore(config)
                if store:
                    stats = store.get_stats()
                    doc_count = stats.get("total_documents", 0)
                    success(f"Faculty data indexed: {doc_count} documents in Chroma")
            else:
                warn("No faculty JSON found — skipping faculty indexing")
    
            # 5b. Ingest distilled Research Cards
            cards_dir = config.BASE_DIR / "research_cards"
            if cards_dir.exists() and list(cards_dir.glob("*.json")):
                store = ingest_research_cards(config)
                if store:
                    stats = store.get_stats()
                    doc_count = stats.get("total_documents", 0)
                    success(f"Research Cards indexed — total docs: {doc_count}")
            else:
                warn("No Research Cards found — skipping card indexing")

        elapsed = time.perf_counter() - t0
        result.mark_done(f"{doc_count} total docs", elapsed)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        fail(f"Indexing failed: {e}")
        traceback.print_exc()
        result.mark_failed(str(e)[:80], elapsed)


# ─── Stage 6: Build Knowledge Graph (optional) ───────────────────────────────

def stage_graph(config, result: StageResult):
    """Build the knowledge graph from crawled data and Research Cards."""
    from src.knowledge_graph.graph_builder import GraphBuilder
    t0 = time.perf_counter()

    builder = GraphBuilder(config=config)
    if not builder.site_graph_path.exists():
        warn(f"{builder.site_graph_path} not found — graph build skipped")
        warn("This file is generated during the Crawl stage (Stage 1)")
        result.mark_skipped("No site_graph.gml")
        return

    try:
        builder.load_site_graph()
        builder.load_faculty_data()
        builder.merge_research_cards()
        builder.export()
        elapsed = time.perf_counter() - t0

        graph_path = Path("data/tiger_brain.json")
        success(f"Knowledge graph built → {graph_path}")
        result.mark_done("graph exported", elapsed)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        fail(f"Graph build failed: {e}")
        traceback.print_exc()
        result.mark_failed(str(e)[:80], elapsed)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TigerResearchBuddy — End-to-End Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                         # Full restricted run
  python run_pipeline.py --mode full             # Full CS department run
  python run_pipeline.py --skip-crawl            # Skip crawl, do rest
  python run_pipeline.py --skip-crawl --skip-scholar --skip-download
        """
    )
    parser.add_argument(
        "--mode", choices=["restricted", "full"], default="restricted",
        help="Pipeline mode: 'restricted' (small/fast) or 'full' (all CS faculty)"
    )
    parser.add_argument("--skip-crawl",    action="store_true", help="Skip Stage 1: Crawl")
    parser.add_argument("--skip-scholar",  action="store_true", help="Skip Stage 2: Scholar enrichment")
    parser.add_argument("--skip-download", action="store_true", help="Skip Stage 3: Paper download")
    parser.add_argument("--skip-distill",  action="store_true", help="Skip Stage 4: PDF distillation")
    parser.add_argument("--skip-index",    action="store_true", help="Skip Stage 5: Vector store indexing")
    parser.add_argument("--skip-graph",    action="store_true", help="Skip Stage 6: Knowledge graph")
    
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint (skips crawl/scholar/download)")

    args = parser.parse_args()
    
    if args.resume:
        args.skip_crawl = True
        args.skip_scholar = True
        args.skip_download = True

    # ── Load config ──────────────────────────────────────────────────────────
    from src.utils.config import RESTRICTED_CONFIG, FULL_CONFIG
    config = FULL_CONFIG if args.mode == "full" else RESTRICTED_CONFIG

    # ── Header ───────────────────────────────────────────────────────────────
    console.print(Panel.fit(
        f"[bold orange1]🐅 TigerResearchBuddy Pipeline[/]\n\n"
        f"Mode:      [cyan]{args.mode.upper()}[/]\n"
        f"Start URL: [dim]{config.START_URLS[0]}[/]\n"
        f"Max profiles: [cyan]{config.MAX_PROFILES}[/]   "
        f"Papers/faculty: [cyan]{config.PAPER_LIMIT_PER_FACULTY}[/]",
        border_style="orange1"
    ))

    # ── Stage results collector ───────────────────────────────────────────────
    r_crawl    = StageResult("1. Crawl")
    r_scholar  = StageResult("2. Scholar Enrich")
    r_download = StageResult("3. Download Papers")
    r_distill  = StageResult("4. Distill Papers")
    r_index    = StageResult("5. Index")
    r_graph    = StageResult("6. Knowledge Graph")
    results = [r_crawl, r_scholar, r_download, r_distill, r_index, r_graph]

    data = {}

    # ── Stage 1: Crawl ───────────────────────────────────────────────────────
    stage_banner(1, "Crawl RIT CS Faculty")
    if args.skip_crawl:
        warn("Skipped by --skip-crawl flag")
        r_crawl.mark_skipped("--skip-crawl")
        # Try to load existing data so downstream stages still work
        if config.OUTPUT_FILE.exists():
            with open(config.OUTPUT_FILE) as f:
                data = json.load(f)
            console.print(f"[dim]Loaded existing data: {len(data.get('faculty', []))} faculty[/]")
        else:
            warn(f"Warning: {config.OUTPUT_FILE} not found — downstream stages still may fail")
    else:
        data = stage_crawl(config, r_crawl)
        if r_crawl.status == "failed":
            console.print("[red]Stage 1 failed. Cannot continue — aborting.[/]")
            print_summary(results)
            return

    # Apply faculty deduplication to the loaded/crawled data
    if data and data.get("faculty"):
        from src.utils.dedup import deduplicate_faculty
        original_count = len(data["faculty"])
        data["faculty"] = deduplicate_faculty(data["faculty"])
        dedup_count = len(data["faculty"])
        if original_count > dedup_count:
            console.print(f"[cyan]Deduped {original_count} → {dedup_count} unique faculty[/]")

    # ── Stage 2: Scholar Enrichment ──────────────────────────────────────────
    stage_banner(2, "Google Scholar Enrichment")
    if args.skip_scholar:
        warn("Skipped by --skip-scholar flag")
        r_scholar.mark_skipped("--skip-scholar")
    else:
        data = stage_scholar(config, data, r_scholar)

    # ── Stage 3: Download Papers ──────────────────────────────────────────────
    stage_banner(3, "Download Research Papers")
    if args.skip_download:
        warn("Skipped by --skip-download flag")
        r_download.mark_skipped("--skip-download")
    else:
        stage_download(config, data, r_download)

    # ── Stage 4: Distill Papers ───────────────────────────────────────────────
    stage_banner(4, "Distill PDFs → Research Cards")
    if args.skip_distill:
        warn("Skipped by --skip-distill flag")
        r_distill.mark_skipped("--skip-distill")
    else:
        stage_distill(config, r_distill)

    # ── Stage 5: Index into Vector Store ─────────────────────────────────────
    stage_banner(5, "Index into Vector Store")
    if args.skip_index:
        warn("Skipped by --skip-index flag")
        r_index.mark_skipped("--skip-index")
    else:
        stage_index(config, r_index)

    # ── Stage 6: Knowledge Graph ──────────────────────────────────────────────
    stage_banner(6, "Build Knowledge Graph (optional)")
    if args.skip_graph:
        warn("Skipped by --skip-graph flag")
        r_graph.mark_skipped("--skip-graph")
    else:
        stage_graph(config, r_graph)

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(results)


if __name__ == "__main__":
    main()
