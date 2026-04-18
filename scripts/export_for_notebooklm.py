"""
Export codebase to a single text file optimized for NotebookLM ingestion.

Key improvements over the naive "dump everything" approach:
  1. Exclude noise:  test results, debug scripts, legacy code, experiments,
     benchmark outputs, log files, __init__.py stubs, and generated artifacts.
  2. Truncate massive files:  tag taxonomies, giant crawlers, etc. get capped
     so they don't crowd out the context window.
  3. Structured preamble:  A human-readable project summary at the top gives
     NotebookLM an anchoring context before it sees any code.
  4. Semantic ordering:  docs → prompts → core src → support files, so the
     most important context appears first in the token window.
  5. Per-file summaries:  each file header includes its purpose line from
     docstrings/comments when available, giving NotebookLM navigation cues.
  6. Token estimation:  tracks approximate token count against NotebookLM's
     500K source limit so you know before uploading.
  7. Auto-generated TOC:  a navigable table of contents by module.
  8. Import graph:  shows which modules depend on which, giving NotebookLM
     architectural awareness.
  9. CLI flags:  --dry-run, --verbose, --max-tokens, --focus for flexibility.
  10. Deduplication:  prevents the same file from appearing twice.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "notebookllm_source.txt"

# Approximate chars-per-token ratio for code (conservative estimate)
CHARS_PER_TOKEN = 3.5
NOTEBOOKLM_TOKEN_LIMIT = 500_000

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Directories to completely skip during traversal
SKIP_DIRS = {
    ".git", "__pycache__", "venv", "env", ".venv", "node_modules",
    ".gemini", ".pytest_cache", ".mypy_cache", ".cache", ".next",
    "benchmark_results", "embedding_benchmark", "pdf_distillation",
    "smart_scraper", "root_sandbox",
    "fixtures", "output", "results",  # test fixtures/output/results
    "lib",        # vendored JS libs (vis.js, tom-select) — no value for LLM
    "logs",       # ephemeral runtime logs
    "screenshots",  # binary-adjacent, useless as text
    "public",     # Next.js static assets
}

# Top-level directories to entirely exclude
EXCLUDE_TOP_DIRS = {
    "legacy",       # dead code — superseded by current src/
    "experiments",  # one-off experiment notebooks/outputs
}

# Specific files to always skip (basenames or relative paths)
SKIP_FILES = {
    # Self-referential / generated dumps
    "notebookllm_source.txt",
    "export_for_notebooklm.py",
    "frontend_dump_for_figma.txt",
    # Config noise
    ".DS_Store",
    ".coverage",
    ".env",
    ".env.example",
    "package-lock.json",
    "next-env.d.ts",
    "eslint.config.mjs",
    "postcss.config.mjs",
    "pytest.ini",
    # Frontend build config (low signal)
    "tsconfig.json",
    "tsconfig.tsbuildinfo",
    # Test output artifacts
    "test_output.txt",
}

# Patterns for files to skip (matched against relative path)
SKIP_PATTERNS = [
    r"^\.streamlit/",           # Streamlit config
    r"^\.tmp_dagster_home",     # Dagster temp dirs (glob, not hardcoded names)
    r"tests/results/",          # Huge test result dumps
    r"tests/output/",           # Test output artifacts
    r"tests/fixtures/",         # Test fixture data
    r"scripts/debug/",          # Debug-only scripts
    r"scripts/test_",           # One-off test scripts in scripts/
    r"scripts/verify_",         # One-off verify scripts
    r"scripts/inspect_",        # One-off inspect scripts
    r"scripts/debug_",          # Debug scripts
    r"scripts/patch_",          # One-off patch scripts
    r"scripts/benchmark_",      # Benchmark scripts
    r"scripts/compare_",        # Comparison scripts
    r"scripts/extract_",        # Extraction scripts
    r"scripts/simulate_",       # Simulation scripts
    r"scripts/run_vision_",     # Vision pilot scripts
    r"scripts/run_micro_",      # Micro pilot scripts
    r"tests/debug_",            # Debug test helpers
    r"tests/migrate",           # Migration scripts in tests
    r"tests/run_standalone",    # Standalone test runners
    r"tests/manual_",           # Manual test runners
    r"tests/generate_fixtures", # Fixture generators
    r"logs/",                   # Log files
]

# Pre-compile patterns for performance
_COMPILED_SKIP_PATTERNS = [re.compile(p) for p in SKIP_PATTERNS]

# Allowed file extensions
ALLOWED_EXTS = {".py", ".md", ".yaml", ".yml", ".toml", ".txt", ".tsx", ".ts", ".css"}

# Maximum lines per file before truncation (keeps head + tail)
MAX_LINES_PER_FILE = 300

# Files that are always included in full (no truncation), by relative path
NEVER_TRUNCATE = {
    "README.md",
    "docs/project_journey.md",
    "src/chatbot/query_engine.py",
    "src/chatbot/rag_engine.py",
    "src/retrieval/hybrid_retriever.py",
    "src/generation/synthesizer.py",
    "src/database/vector_store.py",
    "src/knowledge_graph/graph_builder.py",
    "src/knowledge_graph/builder.py",
    "web_app.py",
    "api.py",
}

# Skip __init__.py files that are stubs (< 5 non-empty lines)
INIT_STUB_THRESHOLD = 5

# ──────────────────────────────────────────────────────────────────────────────
# ORDERING — controls what NotebookLM sees first in its context window
# ──────────────────────────────────────────────────────────────────────────────
# Lower number = appears earlier in the output
PRIORITY_ORDER = {
    "README.md": 0,
    "docs/": 10,
    "data/prompts/": 20,
    "src/chatbot/": 30,
    "src/retrieval/": 31,
    "src/generation/": 32,
    "src/knowledge_graph/": 33,
    "src/database/": 34,
    "src/processors/": 35,
    "src/crawlers/": 36,
    "src/analysis/": 37,
    "src/collaboration/": 38,
    "src/utils/": 39,
    "src/visualization/": 40,
    "src/ui/": 41,
    "src/pipeline_v2/": 42,
    "src/memory/": 43,
    "src/": 44,
    "main.py": 50,
    "web_app.py": 51,
    "api.py": 52,
    "run_pipeline.py": 53,
    "frontend/": 60,
    "scripts/": 70,
    "tests/": 80,
    "pyproject.toml": 90,
    "requirements.txt": 91,
}


def get_priority(rel_path: str) -> int:
    """Return sort priority for a file. Lower = earlier."""
    # Exact match first
    if rel_path in PRIORITY_ORDER:
        return PRIORITY_ORDER[rel_path]
    # Prefix match (longest prefix wins)
    for prefix, prio in sorted(PRIORITY_ORDER.items(), key=lambda x: -len(x[0])):
        if rel_path.startswith(prefix):
            return prio
    return 100  # default


def should_skip(rel_path: str, basename: str) -> bool:
    """Return True if this file should be excluded from the export."""
    # Skip listed files
    if basename in SKIP_FILES:
        return True

    # Skip hidden files
    if basename.startswith("."):
        return True

    # Check extension
    ext = os.path.splitext(basename)[1].lower()
    if ext not in ALLOWED_EXTS and basename != "Makefile":
        return True

    # Skip data/ except prompts/
    if rel_path.startswith("data/") and not rel_path.startswith("data/prompts/"):
        return True

    # Skip patterns (pre-compiled)
    for pattern in _COMPILED_SKIP_PATTERNS:
        if pattern.search(rel_path):
            return True

    return False


def extract_docstring(content: str, ext: str) -> Optional[str]:
    """Try to extract the first docstring or top comment as a file summary."""
    if ext == ".py":
        # Match module-level docstring
        m = re.match(r'^(?:#!/.*\n)?(?:#.*\n)*\s*(?:\"\"\"(.*?)\"\"\")', content, re.DOTALL)
        if m:
            doc = m.group(1).strip()
            # Take just the first paragraph/sentence
            first_line = doc.split("\n\n")[0].split("\n")[0].strip()
            if len(first_line) > 20:
                return first_line[:200]
    elif ext == ".md":
        # First heading
        m = re.match(r'^#\s+(.+)', content, re.MULTILINE)
        if m:
            return m.group(1).strip()[:200]
    elif ext in (".ts", ".tsx"):
        # JSDoc or // comment at top
        m = re.match(r'^/\*\*(.*?)\*/', content, re.DOTALL)
        if m:
            return m.group(1).strip().split("\n")[0].strip(" *")[:200]
    return None


def extract_classes_and_functions(content: str, ext: str) -> Optional[str]:
    """Extract top-level classes and key functions for a structural overview."""
    if ext != ".py":
        return None

    items = []
    for m in re.finditer(r'^class\s+(\w+)(?:\(([^)]*)\))?:', content, re.MULTILINE):
        name = m.group(1)
        bases = m.group(2) or ""
        # Try to grab the class docstring
        pos = m.end()
        doc_match = re.match(r'\s*"""(.+?)"""', content[pos:], re.DOTALL)
        doc = ""
        if doc_match:
            doc = doc_match.group(1).strip().split("\n")[0][:80]
        if bases:
            items.append(f"  class {name}({bases})" + (f" — {doc}" if doc else ""))
        else:
            items.append(f"  class {name}" + (f" — {doc}" if doc else ""))

    # Only grab top-level def (not indented)
    for m in re.finditer(r'^def\s+(\w+)\(', content, re.MULTILINE):
        name = m.group(1)
        if not name.startswith("_"):
            items.append(f"  def {name}()")

    if items:
        return "\n".join(items[:10])  # Cap at 10 to avoid noise
    return None


def extract_imports(content: str, ext: str, rel_path: str) -> List[str]:
    """Extract internal project imports from a Python file."""
    if ext != ".py":
        return []

    imports = []
    for m in re.finditer(
        r'^(?:from\s+(src\.\S+|\.+\S*)|import\s+(src\.\S+))\s',
        content,
        re.MULTILINE,
    ):
        module = m.group(1) or m.group(2)
        if module:
            # Normalize relative imports
            if module.startswith("."):
                # Resolve relative to current file's package
                parts = rel_path.replace("/", ".").rsplit(".", 2)
                if len(parts) >= 2:
                    pkg = parts[0]
                    # Strip leading dots and prepend package
                    clean = module.lstrip(".")
                    module = f"{pkg}.{clean}" if clean else pkg
            imports.append(module.split(" ")[0])  # Strip "import X" suffix
    return imports


def truncate_content(content: str, rel_path: str) -> Tuple[str, bool]:
    """Truncate long files, keeping head and tail with a marker.

    Returns (content, was_truncated).
    """
    if rel_path in NEVER_TRUNCATE:
        return content, False

    lines = content.split("\n")
    if len(lines) <= MAX_LINES_PER_FILE:
        return content, False

    head_lines = MAX_LINES_PER_FILE * 2 // 3   # ~200 lines from top
    tail_lines = MAX_LINES_PER_FILE - head_lines  # ~100 lines from bottom
    omitted = len(lines) - head_lines - tail_lines

    head = "\n".join(lines[:head_lines])
    tail = "\n".join(lines[-tail_lines:])

    truncated = f"{head}\n\n# ... [{omitted} lines omitted for brevity] ...\n\n{tail}"
    return truncated, True


def is_stub_init(content: str) -> bool:
    """Return True if this __init__.py is basically empty."""
    meaningful = [l for l in content.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
    return len(meaningful) < INIT_STUB_THRESHOLD


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return int(len(text) / CHARS_PER_TOKEN)


def build_toc(files: List[Tuple[int, str, str, str, str, Optional[str]]]) -> str:
    """Build a table of contents grouped by module/directory."""
    toc_lines = ["## Table of Contents\n"]
    toc_lines.append("| # | Module | File | Summary |")
    toc_lines.append("|---|--------|------|---------|")

    for i, (_, rel_path, _, _, _, summary) in enumerate(files, 1):
        module = rel_path.split("/")[0] if "/" in rel_path else "root"
        basename = os.path.basename(rel_path)
        desc = summary[:60] + "…" if summary and len(summary) > 60 else (summary or "—")
        toc_lines.append(f"| {i} | `{module}` | `{basename}` | {desc} |")

    toc_lines.append("")
    return "\n".join(toc_lines)


def build_import_graph(import_map: Dict[str, List[str]]) -> str:
    """Build a human-readable dependency summary for key modules."""
    if not import_map:
        return ""

    lines = ["\n## Module Dependency Map\n"]
    lines.append("This shows which internal modules each file imports, revealing")
    lines.append("the architectural dependencies between components.\n")

    # Group by top-level package
    by_package: Dict[str, List[Tuple[str, List[str]]]] = defaultdict(list)
    for rel_path, imports in sorted(import_map.items()):
        if not imports:
            continue
        pkg = rel_path.split("/")[0] if "/" in rel_path else "root"
        by_package[pkg].append((rel_path, imports))

    for pkg in sorted(by_package.keys()):
        entries = by_package[pkg]
        if not entries:
            continue
        lines.append(f"### {pkg}/")
        for rel_path, imports in entries:
            basename = os.path.basename(rel_path)
            unique_imports = sorted(set(imports))[:8]  # Cap verbosity
            import_str = ", ".join(f"`{i}`" for i in unique_imports)
            lines.append(f"- **{basename}** → {import_str}")
        lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# PREAMBLE — a structured summary injected at the top of the export
# ──────────────────────────────────────────────────────────────────────────────
PREAMBLE_TEMPLATE = """\
# Tiger Research Buddy — Complete Knowledge Base

This document contains the architecture documentation, LLM prompt configurations,
and source code for **TigerResearchBuddy**, an AI-powered research discovery and
collaboration platform for Rochester Institute of Technology (RIT).

**Export Stats:** {file_count} files · {total_lines:,} lines · ~{token_estimate:,} tokens ({token_pct:.0f}% of NotebookLM limit)

## What This Project Does

TigerResearchBuddy helps RIT students and faculty:
- **Discover research** across Computing, Engineering, Science, and other colleges
- **Find collaborators** using AI-powered matching between research ideas and faculty expertise
- **Explore connections** via an interactive knowledge graph ("TigerBrain")
- **Analyze impact** with UN SDG alignment scoring

## Technical Architecture (Hybrid RAG)

The system uses a **Two-Lobe Brain** architecture:
1. **Left Lobe (Vector Search)**: ChromaDB/LanceDB stores document embeddings
   (sentence-transformers/all-MiniLM-L6-v2) for semantic similarity search.
2. **Right Lobe (Knowledge Graph)**: NetworkX graph with Faculty, Paper, Concept,
   and Method nodes connected by AUTHORED_BY, CITES, STUDIES edges.

Query flow: Intent Classification → Query Expansion → Hybrid Retrieval
(vector + graph) → Context Enrichment → LLM Generation (Gemini/Ollama)
→ Response Post-processing with citations.

## Data Pipeline

Web Crawlers (RIT sites) → Smart Extraction (LLM) → Paper Download (ArXiv/S2)
→ DeepDistiller (VLM PDF processing) → Research Cards → Knowledge Graph Builder
→ Entity Resolution → Vector Store indexing.

## Key Modules

| Module | Purpose |
|--------|---------|
| `src/chatbot/query_engine.py` | Core RAG query processing with Chain-of-Density |
| `src/chatbot/rag_engine.py` | RAG pipeline orchestration |
| `src/retrieval/hybrid_retriever.py` | Dual vector+graph retrieval with RRF fusion |
| `src/retrieval/reranker.py` | Cross-encoder second-stage precision reranking |
| `src/generation/synthesizer.py` | Chain-of-Density response synthesis |
| `src/knowledge_graph/builder.py` | Knowledge graph construction |
| `src/database/vector_store.py` | ChromaDB/LanceDB vector storage |
| `src/processors/pdf_distiller.py` | Vision-first PDF extraction |
| `src/crawlers/smart_crawler.py` | LLM-powered web scraping |
| `src/memory/session_store.py` | Dual-tier conversational memory |
| `web_app.py` | Streamlit web interface |
| `api.py` | FastAPI REST backend |
| `data/prompts/` | LLM persona and instruction prompts |

---

"""


def export_codebase(
    dry_run: bool = False,
    verbose: bool = False,
    max_tokens: int = NOTEBOOKLM_TOKEN_LIMIT,
    focus: Optional[str] = None,
    output_path: Optional[Path] = None,
):
    """Main export function.

    Parameters
    ----------
    dry_run : bool
        If True, print stats but don't write the output file.
    verbose : bool
        If True, print each included/skipped file.
    max_tokens : int
        Stop including files once the estimated token count exceeds this.
    focus : str or None
        If provided, only include files whose path contains this substring.
        Example: --focus src/chatbot to export only chatbot module + docs.
    output_path : Path or None
        Override default output file path.
    """
    if output_path is None:
        output_path = OUTPUT_FILE

    collected_files: List[Tuple[int, str, str, str, str, Optional[str]]] = []
    # (priority, rel_path, lang, header, content, summary)

    seen_paths: Set[str] = set()  # Deduplication guard
    import_map: Dict[str, List[str]] = {}
    skipped_count = 0
    skipped_reasons: Dict[str, int] = defaultdict(int)
    truncated_files: List[str] = []
    total_original_lines = 0

    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        # Remove ignored directories in-place
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS
                              and not d.startswith(".tmp_dagster_home"))

        # Check top-level exclusions
        rel_dir = os.path.relpath(dirpath, ROOT_DIR)
        top_dir = rel_dir.split(os.sep)[0] if rel_dir != "." else ""
        if top_dir in EXCLUDE_TOP_DIRS:
            dirnames.clear()
            continue

        filenames.sort()

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(file_path, ROOT_DIR)
            # Normalize path separators
            rel_path = rel_path.replace(os.sep, "/")

            # Focus filter
            if focus and focus not in rel_path and not rel_path.startswith("README"):
                continue

            if should_skip(rel_path, filename):
                skipped_count += 1
                if verbose:
                    print(f"  SKIP: {rel_path}")
                continue

            # Deduplication guard
            if rel_path in seen_paths:
                skipped_reasons["duplicate"] += 1
                if verbose:
                    print(f"  DUP:  {rel_path}")
                continue
            seen_paths.add(rel_path)

            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError):
                skipped_reasons["read_error"] += 1
                continue

            # Skip stub __init__.py
            if filename == "__init__.py" and is_stub_init(content):
                skipped_reasons["stub_init"] += 1
                continue

            # Skip empty files
            if not content.strip():
                skipped_reasons["empty"] += 1
                continue

            # Determine language tag
            ext = os.path.splitext(filename)[1].lower()
            lang_map = {
                ".py": "python", ".md": "markdown", ".yaml": "yaml",
                ".yml": "yaml", ".toml": "toml", ".txt": "text",
                ".tsx": "tsx", ".ts": "typescript", ".css": "css",
            }
            lang = lang_map.get(ext, "text")
            if filename == "Makefile":
                lang = "makefile"

            # Count original lines
            original_lines = content.count("\n") + 1
            total_original_lines += original_lines

            # Extract imports for dependency graph
            imports = extract_imports(content, ext, rel_path)
            if imports:
                import_map[rel_path] = imports

            # Truncate if needed
            content, was_truncated = truncate_content(content, rel_path)
            if was_truncated:
                truncated_files.append(f"{rel_path} ({original_lines} lines)")

            # Extract summary
            summary = extract_docstring(content, ext)

            # Extract structural overview
            structure = extract_classes_and_functions(content, ext)

            # Build header
            header = f"## File: {rel_path}"
            if summary:
                header += f"\n> {summary}"
            if structure:
                header += f"\n\n**Structure:**\n```\n{structure}\n```"

            priority = get_priority(rel_path)
            collected_files.append((priority, rel_path, lang, header, content, summary))

            if verbose:
                tokens = estimate_tokens(content)
                print(f"  ADD:  {rel_path} ({original_lines} lines, ~{tokens:,} tokens)")

    # Sort by priority, then alphabetically within same priority
    collected_files.sort(key=lambda x: (x[0], x[1]))

    # Build full output in memory for token estimation
    parts = []

    # TOC
    toc = build_toc(collected_files)
    parts.append(toc)

    # Import graph
    dep_graph = build_import_graph(import_map)
    if dep_graph:
        parts.append(dep_graph)

    parts.append("---\n\n")

    # File contents
    for _, rel_path, lang, header, content, _ in collected_files:
        parts.append(f"{header}\n\n```{lang}\n{content}\n```\n\n")

    body = "\n".join(parts)
    total_lines = sum(c.count("\n") for _, _, _, _, c, _ in collected_files)

    # Build dynamic preamble with real stats
    token_estimate = estimate_tokens(body)
    preamble = PREAMBLE_TEMPLATE.format(
        file_count=len(collected_files),
        total_lines=total_lines,
        token_estimate=token_estimate,
        token_pct=(token_estimate / max_tokens) * 100,
    )

    full_output = preamble + body

    # Token budget check
    final_tokens = estimate_tokens(full_output)
    over_budget = final_tokens > max_tokens

    # ── Report ──
    size_mb = len(full_output.encode("utf-8")) / 1024 / 1024
    print(f"\n{'═' * 60}")
    print(f"  NotebookLM Export Report")
    print(f"{'═' * 60}")
    print(f"  Files included:    {len(collected_files)}")
    print(f"  Files skipped:     {skipped_count}")
    print(f"  Files truncated:   {len(truncated_files)}")
    print(f"  Original lines:    {total_original_lines:,}")
    print(f"  Output lines:      {total_lines:,}")
    print(f"  Output size:       {size_mb:.2f} MB")
    print(f"  Est. tokens:       {final_tokens:,} / {max_tokens:,}")

    if over_budget:
        overage = final_tokens - max_tokens
        print(f"  ⚠️  OVER BUDGET by ~{overage:,} tokens!")
        print(f"       Consider using --focus to select specific modules")
    else:
        headroom = max_tokens - final_tokens
        print(f"  ✅ Within budget ({headroom:,} tokens remaining)")

    # Breakdown by category
    categories: Dict[str, Tuple[int, int]] = {}  # category -> (file_count, token_count)
    for _, rel_path, _, _, content, _ in collected_files:
        cat = rel_path.split("/")[0] if "/" in rel_path else "root"
        cnt, toks = categories.get(cat, (0, 0))
        categories[cat] = (cnt + 1, toks + estimate_tokens(content))

    print(f"\n  {'Category':<20s} {'Files':>6s} {'~Tokens':>10s} {'%':>6s}")
    print(f"  {'─' * 44}")
    for cat, (count, toks) in sorted(categories.items(), key=lambda x: -x[1][1]):
        pct = (toks / final_tokens * 100) if final_tokens else 0
        print(f"  {cat:<20s} {count:>6d} {toks:>10,} {pct:>5.1f}%")

    if truncated_files and verbose:
        print(f"\n  Truncated files:")
        for tf in truncated_files:
            print(f"    ✂️  {tf}")

    if skipped_reasons and verbose:
        print(f"\n  Skip reasons:")
        for reason, count in sorted(skipped_reasons.items()):
            print(f"    {reason}: {count}")

    print(f"{'═' * 60}\n")

    if dry_run:
        print("🔍 Dry run — no file written.")
        return

    # Write output
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(full_output)

    print(f"✅ Written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Export codebase for NotebookLM ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python scripts/export_for_notebooklm.py                    # Standard export
  python scripts/export_for_notebooklm.py --dry-run           # Preview without writing
  python scripts/export_for_notebooklm.py --verbose            # See every file decision
  python scripts/export_for_notebooklm.py --focus src/chatbot  # Export only chatbot module
  python scripts/export_for_notebooklm.py --max-tokens 200000  # Tighter budget
""",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report without writing the output file.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print each file as it's included or skipped.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=NOTEBOOKLM_TOKEN_LIMIT,
        help=f"Token budget (default: {NOTEBOOKLM_TOKEN_LIMIT:,}).",
    )
    parser.add_argument(
        "--focus",
        type=str,
        default=None,
        help="Only include files whose path contains this substring.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Override output file path.",
    )

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None

    export_codebase(
        dry_run=args.dry_run,
        verbose=args.verbose,
        max_tokens=args.max_tokens,
        focus=args.focus,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
