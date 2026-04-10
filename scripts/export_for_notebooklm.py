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
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "notebookllm_source.txt"

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Directories to completely skip during traversal
SKIP_DIRS = {
    ".git", "__pycache__", "venv", "env", ".venv", "node_modules",
    ".gemini", ".pytest_cache", ".mypy_cache", ".cache", ".next",
    ".tmp_dagster_home_5ive3yay", ".tmp_dagster_home_hz6qc00s",
    ".tmp_dagster_home_jt2ztx1n", ".tmp_dagster_home_nan1geky",
    ".tmp_dagster_home_pmdwo8sv", ".tmp_dagster_home_y_dnx2be",
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
    # Self-referential
    "notebookllm_source.txt",
    "export_for_notebooklm.py",
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
}

# Patterns for files to skip (matched against relative path)
SKIP_PATTERNS = [
    r"^\.streamlit/",           # Streamlit config
    r"^\.tmp_dagster_home",     # Dagster temp dirs
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
    "src/": 43,
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
    # Prefix match
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

    # Skip patterns
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, rel_path):
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


def truncate_content(content: str, rel_path: str) -> str:
    """Truncate long files, keeping head and tail with a marker."""
    if rel_path in NEVER_TRUNCATE:
        return content

    lines = content.split("\n")
    if len(lines) <= MAX_LINES_PER_FILE:
        return content

    head_lines = MAX_LINES_PER_FILE * 2 // 3   # ~200 lines from top
    tail_lines = MAX_LINES_PER_FILE - head_lines  # ~100 lines from bottom
    omitted = len(lines) - head_lines - tail_lines

    head = "\n".join(lines[:head_lines])
    tail = "\n".join(lines[-tail_lines:])

    return f"{head}\n\n# ... [{omitted} lines omitted for brevity] ...\n\n{tail}"


def is_stub_init(content: str) -> bool:
    """Return True if this __init__.py is basically empty."""
    meaningful = [l for l in content.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
    return len(meaningful) < INIT_STUB_THRESHOLD


# ──────────────────────────────────────────────────────────────────────────────
# PREAMBLE — a structured summary injected at the top of the export
# ──────────────────────────────────────────────────────────────────────────────
PREAMBLE = """\
# Tiger Research Buddy — Complete Knowledge Base

This document contains the architecture documentation, LLM prompt configurations,
and source code for **TigerResearchBuddy**, an AI-powered research discovery and
collaboration platform for Rochester Institute of Technology (RIT).

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
| `src/generation/synthesizer.py` | Chain-of-Density response synthesis |
| `src/knowledge_graph/builder.py` | Knowledge graph construction |
| `src/database/vector_store.py` | ChromaDB/LanceDB vector storage |
| `src/processors/pdf_distiller.py` | Vision-first PDF extraction |
| `src/crawlers/smart_crawler.py` | LLM-powered web scraping |
| `web_app.py` | Streamlit web interface |
| `api.py` | FastAPI REST backend |
| `data/prompts/` | LLM persona and instruction prompts |

---

"""


def export_codebase():
    """Main export function."""
    collected_files: List[Tuple[int, str, str, str, str]] = []  # (priority, rel_path, lang, header, content)

    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        # Remove ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

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

            if should_skip(rel_path, filename):
                continue

            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError):
                continue

            # Skip stub __init__.py
            if filename == "__init__.py" and is_stub_init(content):
                continue

            # Skip empty files
            if not content.strip():
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

            # Truncate if needed
            content = truncate_content(content, rel_path)

            # Extract summary
            summary = extract_docstring(content, ext)

            # Build header
            header = f"## File: {rel_path}"
            if summary:
                header += f"\n> {summary}"

            priority = get_priority(rel_path)
            collected_files.append((priority, rel_path, lang, header, content))

    # Sort by priority, then alphabetically within same priority
    collected_files.sort(key=lambda x: (x[0], x[1]))

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(PREAMBLE)

        for _, rel_path, lang, header, content in collected_files:
            out.write(f"{header}\n\n```{lang}\n{content}\n```\n\n")

    size_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"✅ Generated {OUTPUT_FILE}")
    print(f"   Size: {size_mb:.2f} MB")
    print(f"   Files included: {len(collected_files)}")

    # Print breakdown
    categories = {}  # type: dict
    for _, rel_path, *_ in collected_files:
        cat = rel_path.split("/")[0] if "/" in rel_path else "root"
        categories[cat] = categories.get(cat, 0) + 1
    print("\n   Breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"     {cat:20s} {count:3d} files")


if __name__ == "__main__":
    export_codebase()
