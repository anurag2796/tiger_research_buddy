
import argparse
import time
import json
import psutil
import os
import random
import pandas as pd
import tracemalloc
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import List, Dict, Any

# Add src to path
import sys
sys.path.append(os.getcwd())

from src.crawlers.vision_crawler import VisionCrawler

console = Console()

def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def benchmark_engine(engine: str, pdf_paths: List[Path], samples: int) -> Dict[str, Any]:
    """Run benchmark for a specific engine."""
    console.print(f"\n[bold blue]Benchmarking Engine: {engine}[/]")
    
    crawler = VisionCrawler(engine=engine)
    
    # Pre-load models to separate load time from inference time
    t_load_start = time.perf_counter()
    crawler._load_models()
    load_time = time.perf_counter() - t_load_start
    console.print(f"[dim]Model Load Time: {load_time:.2f}s[/]")
    
    results = []
    total_pages = 0
    start_time = time.perf_counter()
    tracemalloc.start()
    
    success_count = 0
    
    for pdf_path in pdf_paths:
        try:
            # Measure per-doc time
            t0 = time.perf_counter()
            mem0 = get_process_memory()
            
            # Run conversion
            res = crawler.convert(str(pdf_path), force_reprocess=True)
            
            dt = time.perf_counter() - t0
            mem1 = get_process_memory()
            peak_mem = tracemalloc.get_traced_memory()[1] / 1024 / 1024
            
            page_count = res.get("metadata", {}).get("page_count", 1) # Default to 1 if missing
            total_pages += page_count
            
            results.append({
                "file": pdf_path.name,
                "pages": page_count,
                "time_sec": dt,
                "time_per_page": dt / page_count,
                "mem_start_mb": mem0,
                "mem_end_mb": mem1,
                "peak_malloc_mb": peak_mem,
                "success": True
            })
            success_count += 1
            console.print(f"  ✓ {pdf_path.name} ({page_count}pg): {dt:.2f}s")
            
        except Exception as e:
            console.print(f"  ✗ {pdf_path.name}: {e}")
            results.append({
                "file": pdf_path.name,
                "success": False,
                "error": str(e)
            })

    tracemalloc.stop()
    total_time = time.perf_counter() - start_time
    
    metrics = {
        "engine": engine,
        "load_time": load_time,
        "total_time": total_time,
        "total_pages": total_pages,
        "success_rate": success_count / len(pdf_paths),
        "avg_time_per_page": total_time / total_pages if total_pages > 0 else 0,
        "throughput_pps": total_pages / total_time if total_time > 0 else 0,
        "results": results
    }
    
    return metrics

def run_benchmarks(pdf_dir: str, samples: int, engines: List[str]):
    pdf_path = Path(pdf_dir)
    all_pdfs = list(pdf_path.glob("*.pdf"))
    
    if not all_pdfs:
        console.print("[red]No PDFs found in data/pdfs[/]")
        return
        
    # Sample
    if len(all_pdfs) > samples:
        selected_pdfs = random.sample(all_pdfs, samples)
    else:
        selected_pdfs = all_pdfs
        
    console.print(f"[bold]Selected {len(selected_pdfs)} PDFs for benchmarking.[/]")
    
    all_metrics = []
    
    for engine in engines:
        metrics = benchmark_engine(engine, selected_pdfs, samples)
        all_metrics.append(metrics)
        
    # Validation & Comparison
    print_comparison_table(all_metrics)
    
    # Save results
    output_dir = Path("docs/benchmarks")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Detailed JSON
    with open(output_dir / "pdf_benchmark_raw.json", "w") as f:
        json.dump(all_metrics, f, indent=2)
        
    # Markdown Summary
    save_markdown_report(all_metrics, output_dir / "pdf_pipeline_v2.md")

def print_comparison_table(metrics_list: List[Dict]):
    table = Table(title="PDF Pipeline Benchmark Results")
    table.add_column("Metric", style="cyan")
    
    for m in metrics_list:
        table.add_column(m["engine"].upper(), style="green")
        
    table.add_row("Success Rate", *[f"{m['success_rate']:.1%}" for m in metrics_list])
    table.add_row("Total Pages", *[str(m["total_pages"]) for m in metrics_list])
    table.add_row("Total Time", *[f"{m['total_time']:.2f}s" for m in metrics_list])
    table.add_row("Time/Page", *[f"{m['avg_time_per_page']:.3f}s" for m in metrics_list])
    table.add_row("Throughput", *[f"{m['throughput_pps']:.2f} pg/s" for m in metrics_list])
    table.add_row("Model Load Time", *[f"{m['load_time']:.2f}s" for m in metrics_list])
    
    console.print(table)

def save_markdown_report(metrics_list: List[Dict], path: Path):
    content = "# PDF Pipeline Benchmark Report\n\n"
    content += f"**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    df_data = {}
    for m in metrics_list:
        name = m['engine']
        df_data[f"{name} (pg/s)"] = m['throughput_pps']
        df_data[f"{name} (s/pg)"] = m['avg_time_per_page']
    
    content += "## Summary Comparison\n\n"
    content += "| Metric | " + " | ".join([m['engine'] for m in metrics_list]) + " |\n"
    content += "|---|---" * len(metrics_list) + "|\n"
    content += f"| **Throughput (pg/s)** | " + " | ".join([f"{m['throughput_pps']:.2f}" for m in metrics_list]) + " |\n"
    content += f"| **Avg Time/Page (s)** | " + " | ".join([f"{m['avg_time_per_page']:.3f}" for m in metrics_list]) + " |\n"
    content += f"| **Success Rate** | " + " | ".join([f"{m['success_rate']:.1%}" for m in metrics_list]) + " |\n"
    
    content += "\n## Detailed Results\n"
    for m in metrics_list:
        content += f"\n### Engine: {m['engine']}\n"
        results = m['results']
        df = pd.DataFrame(results)
        if not df.empty:
            content += df.to_markdown(index=False)
        else:
            content += "No results."
            
    with open(path, "w") as f:
        f.write(content)
    console.print(f"[bold green]Report saved to {path}[/]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=5, help="Number of PDFs to sample")
    parser.add_argument("--engines", type=str, default="all", help="Comma separated engines or 'all'")
    parser.add_argument("--file", type=str, help="Specific PDF file to benchmark")
    args = parser.parse_args()
    
    engines = ["marker", "apple_fast"] if args.engines == "all" else args.engines.split(",")
    
    if args.file:
        # Run on specific file
        fpath = Path(args.file)
        if not fpath.exists():
            console.print(f"[red]File not found: {fpath}[/]")
        else:
            all_metrics = []
            for engine in engines:
                metrics = benchmark_engine(engine, [fpath], 1)
                all_metrics.append(metrics)
            print_comparison_table(all_metrics)
            save_markdown_report(all_metrics, Path("docs/benchmarks/pdf_pipeline_v2.md"))
    else:
        run_benchmarks("data/pdfs", args.samples, engines)
