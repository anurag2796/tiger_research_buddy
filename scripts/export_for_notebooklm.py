"""
Export TigerResearchBuddy content for NotebookLM ingestion.

Modes:
  --mode code        Code + architecture only (default for developers)
  --mode research    Faculty profiles + research cards + knowledge graph
  --mode full        Both combined (best for demos and comprehensive Q&A)

The 'research' mode is what makes NotebookLM genuinely useful for students —
it includes real faculty bios, paper abstracts, research themes, and the
actual knowledge graph relationships so NotebookLM can answer questions like
"who works on NLP at RIT?" with real answers.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_FILE = ROOT_DIR / "notebooklm_source.txt"

CHARS_PER_TOKEN = 3.5
NOTEBOOKLM_TOKEN_LIMIT = 500_000

# ──────────────────────────────────────────────────────────────────────────────
# CODE EXPORT CONFIG
# ──────────────────────────────────────────────────────────────────────────────

SKIP_DIRS = {
    ".git", "__pycache__", "venv", "env", ".venv", "node_modules",
    ".gemini", ".pytest_cache", ".mypy_cache", ".cache", ".next",
    "benchmark_results", "embedding_benchmark", "pdf_distillation",
    "smart_scraper", "root_sandbox",
    "fixtures", "output", "results",
    "lib", "logs", "screenshots", "public",
}

EXCLUDE_TOP_DIRS = {"legacy", "experiments"}

SKIP_FILES = {
    "notebookllm_source.txt", "export_for_notebooklm.py",
    ".DS_Store", ".coverage", ".env", ".env.example",
    "package-lock.json", "next-env.d.ts", "eslint.config.mjs",
    "postcss.config.mjs", "pytest.ini", "tsconfig.json",
    "tsconfig.tsbuildinfo", "test_output.txt",
}

SKIP_PATTERNS = [
    r"^\.streamlit/", r"tests/results/", r"tests/output/", r"tests/fixtures/",
    r"scripts/debug/", r"scripts/test_", r"scripts/verify_", r"scripts/inspect_",
    r"scripts/debug_", r"scripts/patch_", r"scripts/benchmark_", r"scripts/compare_",
    r"scripts/extract_", r"scripts/simulate_", r"scripts/run_vision_", r"scripts/run_micro_",
    r"tests/debug_", r"tests/migrate", r"tests/run_standalone", r"tests/manual_",
    r"tests/generate_fixtures", r"logs/",
]
_COMPILED_SKIP_PATTERNS = [re.compile(p) for p in SKIP_PATTERNS]

ALLOWED_EXTS = {".py", ".md", ".yaml", ".yml", ".toml", ".txt", ".tsx", ".ts", ".css"}
MAX_LINES_PER_FILE = 300

NEVER_TRUNCATE = {
    "README.md", "src/retrieval/hybrid_retriever.py",
    "src/generation/synthesizer.py", "src/database/vector_store.py",
    "src/knowledge_graph/graph_builder.py", "api.py",
}

PRIORITY_ORDER = {
    "README.md": 0, "docs/": 10, "data/prompts/": 20,
    "src/chatbot/": 30, "src/retrieval/": 31, "src/generation/": 32,
    "src/knowledge_graph/": 33, "src/database/": 34, "src/processors/": 35,
    "src/crawlers/": 36, "src/analysis/": 37, "src/collaboration/": 38,
    "src/utils/": 39, "src/memory/": 43, "src/": 44,
    "main.py": 50, "api.py": 52, "frontend/": 60, "scripts/": 70,
    "tests/": 80, "requirements.txt": 91,
}


# ──────────────────────────────────────────────────────────────────────────────
# RESEARCH DATA EXPORT
# ──────────────────────────────────────────────────────────────────────────────

def load_faculty_profiles(data_dir: Path) -> List[Dict]:
    faculty_file = data_dir / "rit_data_v2.json"
    if not faculty_file.exists():
        return []
    with open(faculty_file) as f:
        return json.load(f).get("faculty", [])


def load_research_cards(data_dir: Path) -> List[Dict]:
    cards_dir = data_dir / "research_cards"
    if not cards_dir.exists():
        return []
    cards = []
    for f in sorted(cards_dir.glob("*.json")):
        try:
            cards.append(json.load(open(f)))
        except Exception:
            pass
    return cards


def load_graph(data_dir: Path) -> Dict:
    graph_file = data_dir / "tiger_brain.json"
    if not graph_file.exists():
        return {"nodes": [], "links": []}
    with open(graph_file) as f:
        return json.load(f)


def build_faculty_section(faculty_list: List[Dict]) -> str:
    if not faculty_list:
        return ""

    lines = [
        "# RIT Faculty Research Profiles",
        "",
        f"This section contains profiles of {len(faculty_list)} RIT faculty members "
        f"with their research interests, departments, and publications.",
        "",
    ]

    # Group by department
    by_dept: Dict[str, List[Dict]] = defaultdict(list)
    for f in faculty_list:
        dept = f.get("department") or f.get("college") or "Unknown"
        by_dept[dept].append(f)

    for dept in sorted(by_dept.keys()):
        members = by_dept[dept]
        lines.append(f"## Department: {dept} ({len(members)} faculty)")
        lines.append("")

        for f in members:
            name = f.get("name", "Unknown")
            title = f.get("title", "")
            email = f.get("email", "")
            url = f.get("url", "")
            bio = f.get("bio") or f.get("description") or f.get("research_interests") or ""
            papers = f.get("papers") or f.get("publications") or []

            lines.append(f"### {name}")
            if title:
                lines.append(f"**Title:** {title}")
            if email:
                lines.append(f"**Email:** {email}")
            if url:
                lines.append(f"**Profile:** {url}")
            if bio:
                # Truncate very long bios
                bio_text = bio if len(bio) < 800 else bio[:800] + "..."
                lines.append(f"**Research Interests / Bio:** {bio_text}")

            if papers:
                lines.append(f"**Selected Publications ({len(papers)} total):**")
                for p in papers[:5]:
                    if isinstance(p, str):
                        lines.append(f"  - {p}")
                    elif isinstance(p, dict):
                        title_p = p.get("title") or p.get("name", "")
                        year = p.get("year", "")
                        venue = p.get("venue") or p.get("journal") or p.get("conference") or ""
                        entry = f"  - {title_p}"
                        if year:
                            entry += f" ({year})"
                        if venue:
                            entry += f" — {venue}"
                        lines.append(entry)
                if len(papers) > 5:
                    lines.append(f"  - ... and {len(papers) - 5} more")

            lines.append("")

    return "\n".join(lines)


def build_research_cards_section(cards: List[Dict]) -> str:
    if not cards:
        return ""

    lines = [
        "# Research Paper Summaries (Distilled Knowledge Cards)",
        "",
        f"This section contains AI-distilled summaries of {len(cards)} research papers "
        "from RIT faculty. Each card includes the paper's core findings, methodology, "
        "and key concepts extracted by TigerResearchBuddy's DeepDistiller pipeline.",
        "",
    ]

    # Group by primary domain
    by_domain: Dict[str, List[Dict]] = defaultdict(list)
    for card in cards:
        bib = card.get("bibliographic_data") or {}
        domain = bib.get("primary_domain") or card.get("domain") or "General"
        # Simplify domain labels
        domain = domain.split(".")[0] if "." in domain else domain
        by_domain[domain].append(card)

    for domain in sorted(by_domain.keys()):
        domain_cards = by_domain[domain]
        lines.append(f"## Research Area: {domain} ({len(domain_cards)} papers)")
        lines.append("")

        for card in domain_cards:
            bib = card.get("bibliographic_data") or {}
            core = card.get("core_content") or {}
            kg = card.get("knowledge_graph") or {}

            title = bib.get("title") or card.get("title") or "Untitled"
            year = bib.get("year") or card.get("year") or ""
            authors = bib.get("authors") or card.get("authors") or []
            abstract = bib.get("abstract") or ""
            novelty = core.get("novelty_claim") or ""
            methodology = core.get("key_methodology") or ""
            outcomes = core.get("outcomes") or []

            # Format authors
            author_names = []
            for a in authors[:4]:
                if isinstance(a, str):
                    author_names.append(a)
                elif isinstance(a, dict):
                    author_names.append(a.get("name", ""))
            author_str = ", ".join(filter(None, author_names))
            if len(authors) > 4:
                author_str += f" et al."

            lines.append(f"### {title}")
            if author_str:
                lines.append(f"**Authors:** {author_str}" + (f" ({year})" if year else ""))
            if abstract:
                lines.append(f"**Abstract:** {abstract[:400]}{'...' if len(abstract) > 400 else ''}")
            if novelty:
                lines.append(f"**Key Contribution:** {novelty}")
            if methodology:
                lines.append(f"**Methodology:** {methodology}")
            if outcomes:
                outcomes_list = outcomes if isinstance(outcomes, list) else [outcomes]
                lines.append("**Outcomes:**")
                for o in outcomes_list[:3]:
                    lines.append(f"  - {o}")

            # Key concepts from KG
            kg_nodes = kg.get("nodes", [])
            concepts = [n.get("label") or n.get("name", "") for n in kg_nodes if isinstance(n, dict)]
            concepts = [c for c in concepts if c][:6]
            if concepts:
                lines.append(f"**Key Concepts:** {', '.join(concepts)}")

            lines.append("")

    return "\n".join(lines)


def build_knowledge_graph_section(graph: Dict, faculty_list: List[Dict]) -> str:
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    if not nodes:
        return ""

    # Compute degree
    degree: Dict[str, int] = defaultdict(int)
    node_by_id: Dict[str, Dict] = {}
    for n in nodes:
        node_by_id[str(n.get("id", ""))] = n
    for link in links:
        s = str(link.get("source", ""))
        t = str(link.get("target", ""))
        degree[s] += 1
        degree[t] += 1

    faculty_nodes = [n for n in nodes if (n.get("type") or "").lower() == "faculty"]
    paper_nodes = [n for n in nodes if (n.get("type") or "").lower() == "paper"]
    concept_nodes = [n for n in nodes if (n.get("type") or "").lower() == "concept"]

    # Top connected faculty
    top_faculty = sorted(faculty_nodes, key=lambda n: degree.get(str(n.get("id", "")), 0), reverse=True)[:20]

    # Top concepts
    top_concepts = sorted(concept_nodes, key=lambda n: degree.get(str(n.get("id", "")), 0), reverse=True)[:30]

    lines = [
        "# TigerBrain Knowledge Graph",
        "",
        "The TigerBrain is a knowledge graph connecting RIT faculty, their research papers, "
        "and the concepts/methods those papers study. This enables multi-hop queries like "
        "'find faculty who work on topics related to federated learning' even when faculty "
        "profiles don't explicitly mention those terms.",
        "",
        f"**Graph Statistics:**",
        f"- {len(faculty_nodes)} Faculty nodes",
        f"- {len(paper_nodes)} Paper nodes",
        f"- {len(concept_nodes)} Concept/Method nodes",
        f"- {len(links)} Edges (AUTHORED, MENTIONS, HAS_TOPIC, RELATED_TO)",
        "",
        "## Most Connected Faculty",
        "These faculty have the most research connections in the graph, indicating broad "
        "or prolific research output:",
        "",
    ]

    for n in top_faculty:
        nid = str(n.get("id", ""))
        name = n.get("label") or n.get("name") or nid
        dept = n.get("dept") or ""
        deg = degree.get(nid, 0)
        dept_str = f" ({dept})" if dept else ""
        lines.append(f"- **{name}**{dept_str} — {deg} connections")

    lines.append("")
    lines.append("## Most Connected Research Concepts")
    lines.append("These concepts appear across the most papers, representing RIT's "
                 "core research themes:")
    lines.append("")

    for n in top_concepts:
        nid = str(n.get("id", ""))
        name = n.get("label") or n.get("name") or nid
        if not name or len(name) < 3:
            continue
        deg = degree.get(nid, 0)
        if deg > 1:
            lines.append(f"- **{name}** (appears in {deg} papers)")

    lines.append("")

    # Build faculty→concepts map for top faculty
    lines.append("## Faculty Research Fingerprints")
    lines.append("For each highly-connected faculty member, their primary research concepts:")
    lines.append("")

    for fn in top_faculty[:10]:
        fid = str(fn.get("id", ""))
        fname = fn.get("label") or fn.get("name") or fid

        # Find papers authored by this faculty
        paper_ids = set()
        for link in links:
            s = str(link.get("source", ""))
            t = str(link.get("target", ""))
            if s == fid and node_by_id.get(t, {}).get("type", "").lower() == "paper":
                paper_ids.add(t)
            elif t == fid and node_by_id.get(s, {}).get("type", "").lower() == "paper":
                paper_ids.add(s)

        # Find concepts connected to those papers
        concept_names = set()
        for pid in paper_ids:
            for link in links:
                s = str(link.get("source", ""))
                t = str(link.get("target", ""))
                neighbor = None
                if s == pid:
                    neighbor = t
                elif t == pid:
                    neighbor = s
                if neighbor and node_by_id.get(neighbor, {}).get("type", "").lower() == "concept":
                    cname = node_by_id[neighbor].get("label") or node_by_id[neighbor].get("name", "")
                    if cname and len(cname) > 3:
                        concept_names.add(cname)

        if concept_names:
            concepts_str = ", ".join(sorted(concept_names)[:10])
            lines.append(f"**{fname}** ({len(paper_ids)} papers): {concepts_str}")

    lines.append("")
    return "\n".join(lines)


def build_sample_qa_section(faculty_list: List[Dict], cards: List[Dict]) -> str:
    """Generate sample Q&A pairs to prime NotebookLM's understanding."""

    # Collect a few faculty names and domains for realistic examples
    names = [f.get("name", "") for f in faculty_list[:5] if f.get("name")]
    domains = set()
    for card in cards[:50]:
        bib = card.get("bibliographic_data") or {}
        d = bib.get("primary_domain", "")
        if d:
            domains.add(d.split(".")[0])
    domain_list = sorted(domains)[:6]

    lines = [
        "# Sample Questions TigerResearchBuddy Can Answer",
        "",
        "The following Q&A pairs illustrate the types of questions this system is "
        "designed to handle. Use these as a guide for querying this NotebookLM source.",
        "",
        "## Research Discovery",
        "",
        "**Q: Who at RIT works on machine learning and computer vision?**",
        "A: Look for faculty whose research cards mention CNNs, deep learning, "
        "image classification, object detection, or neural networks. Check their "
        "publication list and knowledge graph connections for concept nodes related "
        "to these topics.",
        "",
        "**Q: What research is being done on natural language processing at RIT?**",
        "A: Search the knowledge graph for concept nodes labeled NLP, text classification, "
        "transformers, BERT, or large language models. The faculty connected to those "
        "concept nodes are the NLP researchers.",
        "",
        "**Q: Which professors are working on cybersecurity or network security?**",
        "A: Faculty in this area typically have papers involving intrusion detection, "
        "cryptography, network forensics, or privacy-preserving systems.",
        "",
        "## Collaboration Matching",
        "",
        "**Q: I want to work on AI for healthcare — who should I contact?**",
        "A: Look for faculty whose papers involve medical imaging, clinical NLP, "
        "health informatics, EHR analysis, or bioinformatics. These represent the "
        "intersection of AI and healthcare research at RIT.",
        "",
        "**Q: I have a research idea about federated learning for IoT devices. "
        "Who could mentor me?**",
        "A: This requires faculty with expertise in both distributed systems/federated "
        "learning AND embedded systems or IoT. Check the knowledge graph for faculty "
        "nodes connected to both concept clusters.",
        "",
        "## Understanding the System",
        "",
        "**Q: How does TigerResearchBuddy find relevant faculty for a query?**",
        "A: It uses hybrid retrieval — ChromaDB vector search (semantic similarity) "
        "is fused with BM25 keyword search using Reciprocal Rank Fusion. Results are "
        "optionally re-ranked by a CrossEncoder. The system also traverses the "
        "TigerBrain knowledge graph to find multi-hop connections.",
        "",
        "**Q: What data does TigerResearchBuddy use?**",
        "A: It crawls RIT faculty profile pages using SmartCrawler (LLM-powered "
        "extraction), downloads papers from ArXiv and Semantic Scholar, then runs "
        "each PDF through DeepDistiller (a VLM pipeline) to produce structured "
        "Research Cards. These cards feed both the ChromaDB vector store and the "
        "NetworkX knowledge graph.",
        "",
        "**Q: How is the knowledge graph built?**",
        "A: The GraphBuilder fuses three sources: the structural site graph from "
        "SmartCrawler, faculty nodes from the crawled JSON, and Research Cards from "
        "DeepDistiller. EntityResolver deduplicates faculty names using fuzzy + "
        "phonetic matching, then AUTHORED/MENTIONS/HAS_TOPIC edges connect everything.",
        "",
    ]

    if names:
        lines += [
            "## Specific Faculty Queries",
            "",
            f"**Q: What does {names[0]} work on?**",
            f"A: Search the research cards for papers authored by {names[0]}, "
            "then look at the concept nodes connected to those papers in the "
            "knowledge graph section.",
            "",
        ]

    return "\n".join(lines)


def export_research_data(data_dir: Path, verbose: bool = False) -> str:
    """Build the full research data section."""
    parts = []

    print("  Loading faculty profiles...")
    faculty = load_faculty_profiles(data_dir)
    print(f"  → {len(faculty)} faculty")

    print("  Loading research cards...")
    cards = load_research_cards(data_dir)
    print(f"  → {len(cards)} cards")

    print("  Loading knowledge graph...")
    graph = load_graph(data_dir)
    print(f"  → {len(graph.get('nodes', []))} nodes, {len(graph.get('links', []))} edges")

    # Q&A priming section (goes first — sets expectations for NotebookLM)
    parts.append(build_sample_qa_section(faculty, cards))
    parts.append("\n---\n")

    # Knowledge graph overview
    parts.append(build_knowledge_graph_section(graph, faculty))
    parts.append("\n---\n")

    # Faculty profiles
    parts.append(build_faculty_section(faculty))
    parts.append("\n---\n")

    # Research card summaries
    parts.append(build_research_cards_section(cards))

    return "\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# CODE EXPORT (unchanged logic, same quality)
# ──────────────────────────────────────────────────────────────────────────────

def get_priority(rel_path: str) -> int:
    if rel_path in PRIORITY_ORDER:
        return PRIORITY_ORDER[rel_path]
    for prefix, prio in sorted(PRIORITY_ORDER.items(), key=lambda x: -len(x[0])):
        if rel_path.startswith(prefix):
            return prio
    return 100


def should_skip(rel_path: str, basename: str) -> bool:
    if basename in SKIP_FILES:
        return True
    if basename.startswith("."):
        return True
    ext = os.path.splitext(basename)[1].lower()
    if ext not in ALLOWED_EXTS and basename != "Makefile":
        return True
    if rel_path.startswith("data/") and not rel_path.startswith("data/prompts/"):
        return True
    for pattern in _COMPILED_SKIP_PATTERNS:
        if pattern.search(rel_path):
            return True
    return False


def extract_docstring(content: str, ext: str) -> Optional[str]:
    if ext == ".py":
        m = re.match(r'^(?:#!/.*\n)?(?:#.*\n)*\s*(?:\"\"\"(.*?)\"\"\")', content, re.DOTALL)
        if m:
            doc = m.group(1).strip()
            first_line = doc.split("\n\n")[0].split("\n")[0].strip()
            if len(first_line) > 20:
                return first_line[:200]
    elif ext == ".md":
        m = re.match(r'^#\s+(.+)', content, re.MULTILINE)
        if m:
            return m.group(1).strip()[:200]
    elif ext in (".ts", ".tsx"):
        m = re.match(r'^/\*\*(.*?)\*/', content, re.DOTALL)
        if m:
            return m.group(1).strip().split("\n")[0].strip(" *")[:200]
    return None


def extract_classes_and_functions(content: str, ext: str) -> Optional[str]:
    if ext != ".py":
        return None
    items = []
    for m in re.finditer(r'^class\s+(\w+)(?:\(([^)]*)\))?:', content, re.MULTILINE):
        name, bases = m.group(1), m.group(2) or ""
        pos = m.end()
        doc_match = re.match(r'\s*"""(.+?)"""', content[pos:], re.DOTALL)
        doc = doc_match.group(1).strip().split("\n")[0][:80] if doc_match else ""
        items.append(f"  class {name}" + (f"({bases})" if bases else "") + (f" — {doc}" if doc else ""))
    for m in re.finditer(r'^def\s+(\w+)\(', content, re.MULTILINE):
        if not m.group(1).startswith("_"):
            items.append(f"  def {m.group(1)}()")
    return "\n".join(items[:10]) if items else None


def extract_imports(content: str, ext: str, rel_path: str) -> List[str]:
    if ext != ".py":
        return []
    imports = []
    for m in re.finditer(r'^(?:from\s+(src\.\S+|\.+\S*)|import\s+(src\.\S+))\s', content, re.MULTILINE):
        module = m.group(1) or m.group(2)
        if module:
            if module.startswith("."):
                parts = rel_path.replace("/", ".").rsplit(".", 2)
                if len(parts) >= 2:
                    pkg = parts[0]
                    clean = module.lstrip(".")
                    module = f"{pkg}.{clean}" if clean else pkg
            imports.append(module.split(" ")[0])
    return imports


def truncate_content(content: str, rel_path: str) -> Tuple[str, bool]:
    if rel_path in NEVER_TRUNCATE:
        return content, False
    lines = content.split("\n")
    if len(lines) <= MAX_LINES_PER_FILE:
        return content, False
    head_lines = MAX_LINES_PER_FILE * 2 // 3
    tail_lines = MAX_LINES_PER_FILE - head_lines
    omitted = len(lines) - head_lines - tail_lines
    head = "\n".join(lines[:head_lines])
    tail = "\n".join(lines[-tail_lines:])
    return f"{head}\n\n# ... [{omitted} lines omitted] ...\n\n{tail}", True


def is_stub_init(content: str) -> bool:
    meaningful = [l for l in content.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
    return len(meaningful) < 5


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def build_toc(files) -> str:
    toc_lines = ["## Table of Contents\n", "| # | Module | File | Summary |", "|---|--------|------|---------|"]
    for i, (_, rel_path, _, _, _, summary) in enumerate(files, 1):
        module = rel_path.split("/")[0] if "/" in rel_path else "root"
        basename = os.path.basename(rel_path)
        desc = (summary[:60] + "…") if summary and len(summary) > 60 else (summary or "—")
        toc_lines.append(f"| {i} | `{module}` | `{basename}` | {desc} |")
    return "\n".join(toc_lines) + "\n"


def build_import_graph(import_map: Dict[str, List[str]]) -> str:
    if not import_map:
        return ""
    lines = ["\n## Module Dependency Map\n"]
    by_package: Dict[str, List] = defaultdict(list)
    for rel_path, imports in sorted(import_map.items()):
        if imports:
            pkg = rel_path.split("/")[0] if "/" in rel_path else "root"
            by_package[pkg].append((rel_path, imports))
    for pkg in sorted(by_package.keys()):
        lines.append(f"### {pkg}/")
        for rel_path, imports in by_package[pkg]:
            basename = os.path.basename(rel_path)
            import_str = ", ".join(f"`{i}`" for i in sorted(set(imports))[:8])
            lines.append(f"- **{basename}** → {import_str}")
        lines.append("")
    return "\n".join(lines)


def export_code(data_dir: Path, verbose: bool = False, focus: Optional[str] = None,
                max_tokens: int = NOTEBOOKLM_TOKEN_LIMIT) -> Tuple[str, dict]:
    """
    Curated code export — only architecturally significant files, with narrative
    explanations between sections so NotebookLM understands the system design.
    """
    # ── Curated file list in reading order ──────────────────────────────────
    # Each entry: (rel_path, narrative_before)
    # narrative_before = prose explanation inserted BEFORE the code block
    CURATED = [
        ("api.py", """
## Component: API Server (api.py)

This is the main entry point for the web application. It is a FastAPI server that:
- Initializes all services (vector store, BM25 index, knowledge graph, LLM client) at startup
- Exposes `/api/chat/stream` — the primary streaming chat endpoint that the frontend uses
- Exposes `/api/graph` — serves the TigerBrain knowledge graph to the GraphViewer
- Exposes `/api/idea` — the Collaboration Hub endpoint for faculty matching

The lifespan context manager wires everything together. The chat endpoint resolves
session IDs, loads conversation history, runs hybrid retrieval, synthesizes a response,
and persists the turn to memory — all in one request.
"""),

        ("src/utils/hardware.py", """
## Component: Hardware Abstraction (hardware.py)

Single source of truth for all hardware-aware decisions. Builds `HW_PROFILE` at import
time by probing PyTorch/CUDA availability. Every concurrency limit, context window size,
embedding device, and PDF engine choice comes from here.

This is why the same codebase runs on a MacBook M4 (fast, 2 parallel slots, MPS embeddings)
and a Jetson AGX Orin (conservative defaults, CUDA embeddings, 1 chat slot). No device
flags are hardcoded anywhere else in the project.
"""),

        ("src/utils/config.py", """
## Component: Configuration (config.py)

Imports HW_PROFILE and exposes the two CrawlConfig presets (RESTRICTED for dev/testing,
FULL for production) and LLMConfig. DATA_DIR is env-var overridable via DATA_DIR_PATH —
this is how the new pipeline run writes to `data_next/` while the demo data in `data/`
stays untouched.
"""),

        ("src/retrieval/hybrid_retriever.py", """
## Component: Hybrid Retriever — the core of the RAG system

This is the most important retrieval component. It fuses two complementary search strategies:

1. **Vector search** (ChromaDB): finds semantically similar content even when exact words
   don't match. "deep neural network" matches "DNN" and "multilayer perceptron".

2. **BM25 keyword search**: finds exact term matches with TF-IDF weighting. Great for
   specific names ("Prof. Sumita Mishra"), acronyms, and technical jargon.

The two result lists are fused using **Reciprocal Rank Fusion (RRF)**:
  score(doc) = 1/(k + vector_rank) + 1/(k + bm25_rank)

where k=60 is a smoothing constant. Documents appearing in both lists get a combined
score boost. Documents only in one list still contribute via their single-source rank.

An optional CrossEncoder reranker (second-stage) re-scores the top-30 RRF results for
precision before returning the final top-k.
"""),

        ("src/database/vector_store.py", """
## Component: Vector Store (ChromaDB wrapper)

Wraps ChromaDB with the nomic-ai/nomic-embed-text-v1.5 embedding model. Handles:
- Document chunking with 1000-char chunks and 200-char overlap (better recall for long docs)
- Batch upsert with deduplication
- Collection management per config mode (rit_research_full vs rit_research_restricted)

The BM25 corpus is built from the same documents at API startup, so both retrieval
paths always see the same data.
"""),

        ("src/generation/synthesizer.py", """
## Component: Response Synthesizer

Takes the retrieved context documents and generates a structured, cited response.

Key behaviors:
- **Conversational short-circuit**: greetings, "what are your capabilities", etc. are
  detected by regex and answered instantly without hitting the LLM or retriever.
- **Structured format**: forces the LLM to output in 4 sections (Direct Answer,
  Key Faculty, Research Areas, Next Steps) with [citation] brackets.
- **History injection**: prepends the sliding-window conversation history so the LLM
  has multi-turn context.
- **Streaming**: `synthesize_stream_async` yields token chunks for SSE — the frontend
  displays tokens as they arrive rather than waiting for the full response.
"""),

        ("src/knowledge_graph/graph_builder.py", """
## Component: Knowledge Graph Builder

Builds the TigerBrain NetworkX graph from three sources:
1. Faculty nodes from the crawled JSON (RIT faculty profiles)
2. Paper nodes from Research Cards (one per distilled PDF)
3. Concept nodes from the knowledge_graph field of each Research Card

Key design decisions:
- Only wires AUTHORED edges to faculty nodes already in the graph (RIT faculty).
  External co-authors are skipped to avoid polluting the graph with thousands of
  "faculty" nodes for people who aren't at RIT.
- Concept IDs are scoped per paper (paper_id__concept_1) to prevent cross-card
  collisions when the LLM outputs generic IDs like "concept_1".
- Both nested TigerCard 2.0 schema (bibliographic_data.title) and flat old schema
  are handled for backwards compatibility.
"""),

        ("src/processors/pdf_distiller.py", """
## Component: DeepDistiller (PDF → Research Card)

The most computationally expensive step in the pipeline. Takes a raw PDF and produces
a structured Research Card JSON with: title, authors, abstract, novelty claim,
methodology, outcomes, and a mini knowledge graph of concepts and relations.

Key design:
- Uses qwen2.5:7b via Ollama. Context window is 16384 (overrides the 8192 global default).
- Text is truncated to 8000 chars before prompting to prevent context overflow.
- GC + CUDA cache clearing after each PDF prevents VRAM fragmentation on the Jetson.
- DISTILLER_CONCURRENCY=3 controls the asyncio semaphore — 3 PDFs distill in parallel,
  matching OLLAMA_NUM_PARALLEL=3.
- Already-done cards are skipped on restart (checkpoint by output file existence).
"""),

        ("src/crawlers/smart_crawler.py", """
## Component: SmartCrawler

LLM-powered web scraper for RIT faculty pages. Uses an LLM to extract structured
faculty data (name, title, email, research interests, publication links) from raw HTML,
which handles the wide variety of faculty page formats across RIT colleges.

The crawler respects rate limits, uses a checkpoint file to resume interrupted runs,
and filters to computing faculty by default (other colleges are commented out in config).
"""),

        ("src/memory/session_store.py", """
## Component: Session Memory (MemoryModule)

Provides conversation continuity across multiple turns. Uses a sliding window of the
last N turns (N = HW_PROFILE.memory_window, default 6 on Jetson) to keep context
manageable while still supporting follow-up questions.

The session_id is minted by the backend and returned to the frontend in the first SSE
event. The frontend persists it in localStorage and sends it with every subsequent
request, so the same session window is loaded across page refreshes.
"""),

        ("src/collaboration/matcher.py", """
## Component: Collaboration Matcher

Powers the "Collaboration Hub" feature. Given a research idea (title + description +
tags), it finds the most semantically similar faculty using the vector store, then
filters and ranks by college affiliation.

Used by the `/api/idea` endpoint together with the ImpactAnalyzer which scores
the idea against UN Sustainable Development Goals.
"""),

        ("src/retrieval/reranker.py", """
## Component: CrossEncoder Reranker (second-stage precision)

After RRF fusion returns top-30 candidates, the CrossEncoder jointly encodes the
query and each document to produce a relevance score. This is slower than bi-encoder
retrieval but much more precise — it catches cases where a document is semantically
similar to the query but actually irrelevant.

Used when `rerank=True` in hybrid_search(). Enabled by default in the API.
"""),

        ("data/prompts/role.md", """
## LLM Prompt: Tiger Persona (role.md)

This is the system prompt that defines TigerResearchBuddy's personality and behavior.
It is loaded by the Ollama client and injected as the `system` message in every chat
request. The persona shapes tone, citation behavior, and how the LLM handles
out-of-scope questions.
"""),

        ("data/prompts/distiller_schema.md", """
## LLM Prompt: Distiller Schema (distiller_schema.md)

The structured extraction prompt given to qwen2.5:7b for each PDF. Defines the exact
JSON schema the model must output, including the nested knowledge_graph with nodes and
edges. This is what drives the Research Card format used everywhere downstream.
"""),

        ("data/prompts/chain_of_density.md", """
## LLM Prompt: Chain of Density (chain_of_density.md)

An advanced prompting technique for high-quality synthesis. The model iteratively
re-reads its own output and adds more specific entities/details in each pass,
producing a denser and more information-rich response. Used with `use_cod=True`.
"""),

        ("frontend/src/components/ChatInterface.tsx", """
## Frontend: Chat Interface

The main chat UI component. Key behaviors:
- Session persistence: captures session_id from the first [SOURCES] SSE event and
  stores it in localStorage. Every subsequent message sends the same session_id,
  giving the backend the context window to load.
- Message persistence: the last 60 messages are stored in localStorage so the
  conversation survives page refreshes.
- Streaming: uses the Fetch API + ReadableStream to process SSE tokens as they arrive.
- Persona switcher: Tiger (default), Analyzer, Critique modes change the system prompt.
"""),

        ("frontend/src/components/GraphViewer.tsx", """
## Frontend: Knowledge Graph Viewer

Interactive force-directed graph using react-force-graph-2d.
- Node size scales with degree (well-connected faculty = bigger nodes)
- Faculty labels always visible when zoom > 0.6; concept labels only when zoomed in
- Click a node → side panel shows type, department, connected papers and concepts
- Search box highlights matching faculty + their neighborhood
- Type filter buttons (All / Faculty / Papers / Concepts)
- Links glow teal between highlighted nodes
"""),

        ("frontend/src/components/CollaborationHub.tsx", """
## Frontend: Collaboration Hub

The research idea matching UI. Student enters a title, description, college, and tags.
The backend runs semantic search against the faculty vector store and returns:
1. Impact score (0-10) with summary and UN SDG alignment
2. Top faculty matches with relevance percentages

This demonstrates the system's value beyond pure search — it actively suggests
who a student should contact for a given research idea.
"""),

        ("main.py", """
## CLI Entry Point (main.py)

Click-based CLI for running the full data pipeline. Key commands:
- `scrape-all --mode full --max-papers 15 --max-profiles 150`: runs all 5 phases
  (crawl → download → distill → index → graph build)
- `chat` / `chat-offline`: interactive chat for testing
- `stats`: show database statistics

The pipeline writes to DATA_DIR (controlled by DATA_DIR_PATH env var), so running
with `DATA_DIR_PATH=data_next` builds a new dataset without touching the demo data.
"""),
    ]

    parts = []
    file_count = 0
    skipped_count = 0

    parts.append("# TigerResearchBuddy — Curated Architecture & Code\n\n")
    parts.append(
        "This document walks through the system architecture in reading order — "
        "each section explains a component's role before showing the actual code. "
        "This is intentionally curated: only the ~18 files that matter architecturally "
        "are included. Boilerplate, test fixtures, and generated files are excluded.\n\n"
    )

    for rel_path, narrative in CURATED:
        full_path = ROOT_DIR / rel_path
        if not full_path.exists():
            if verbose:
                print(f"  MISSING: {rel_path}")
            skipped_count += 1
            continue

        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:
            skipped_count += 1
            continue

        if not content.strip():
            skipped_count += 1
            continue

        ext = full_path.suffix.lower()
        lang_map = {".py": "python", ".md": "markdown", ".yaml": "yaml",
                    ".tsx": "tsx", ".ts": "typescript", ".txt": "text"}
        lang = lang_map.get(ext, "text")

        content, _ = truncate_content(content, rel_path)
        file_count += 1

        if verbose:
            print(f"  ADD: {rel_path}")

        parts.append(narrative.strip())
        parts.append(f"\n\n**`{rel_path}`**\n\n```{lang}\n{content}\n```\n\n---\n")

    body = "\n".join(parts)
    return body, {"files": file_count, "skipped": skipped_count, "truncated": 0, "original_lines": 0}


# ──────────────────────────────────────────────────────────────────────────────
# PREAMBLE
# ──────────────────────────────────────────────────────────────────────────────

def build_preamble(mode: str, stats: dict, token_estimate: int, max_tokens: int,
                   data_dir: Path) -> str:
    # Pull live stats from data if available
    faculty_count = 0
    paper_count = 0
    card_count = 0
    graph_nodes = 0

    try:
        fac_file = data_dir / "rit_data_v2.json"
        if fac_file.exists():
            faculty_count = len(json.load(open(fac_file)).get("faculty", []))
    except Exception:
        pass

    cards_dir = data_dir / "research_cards"
    if cards_dir.exists():
        card_count = len(list(cards_dir.glob("*.json")))

    graph_file = data_dir / "tiger_brain.json"
    try:
        if graph_file.exists():
            g = json.load(open(graph_file))
            graph_nodes = len(g.get("nodes", []))
    except Exception:
        pass

    mode_desc = {
        "code": "source code and architecture documentation",
        "research": "faculty profiles, research paper summaries, and knowledge graph",
        "full": "source code, faculty profiles, research papers, and knowledge graph",
    }.get(mode, "")

    return f"""# TigerResearchBuddy — NotebookLM Knowledge Base
**Mode:** {mode} ({mode_desc})
**Export Stats:** {stats.get('files', 0)} code files · {card_count} research cards · ~{token_estimate:,} tokens ({token_estimate / max_tokens * 100:.0f}% of NotebookLM limit)

## What is TigerResearchBuddy?

TigerResearchBuddy is an AI-powered research discovery and collaboration platform
built for Rochester Institute of Technology (RIT). It helps students find faculty
mentors, discover research opportunities, and explore how RIT's research areas
connect to each other.

## Live Database Stats (as of this export)

- **{faculty_count} RIT Faculty** profiles crawled and indexed
- **{card_count} Research Papers** distilled into structured knowledge cards
- **{graph_nodes} Knowledge Graph Nodes** (faculty + papers + concepts)
- **Vector Store:** ChromaDB with nomic-ai/nomic-embed-text-v1.5 embeddings
- **LLM:** qwen2.5:7b via Ollama (running locally on Jetson AGX Orin 64GB)

## Architecture

**Query path:** User question → Hybrid retrieval (ChromaDB vector + BM25 keyword,
fused via Reciprocal Rank Fusion) → CrossEncoder reranking → qwen2.5:7b synthesis
with citations → Streamed response.

**Data pipeline:** SmartCrawler (RIT web) → PaperDownloader (ArXiv/S2) →
DeepDistiller (VLM PDF → Research Cards) → GraphBuilder (NetworkX knowledge graph)
→ ChromaDB indexing.

---

"""


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Export TigerResearchBuddy for NotebookLM ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python scripts/export_for_notebooklm.py                        # Code only (default)
  python scripts/export_for_notebooklm.py --mode research        # Faculty + papers + graph
  python scripts/export_for_notebooklm.py --mode full            # Everything
  python scripts/export_for_notebooklm.py --mode full --dry-run  # Preview stats
  python scripts/export_for_notebooklm.py --focus src/retrieval  # Single module
""",
    )
    parser.add_argument("--mode", choices=["code", "research", "full"], default="code",
                        help="What to export: code, research data, or full (default: code)")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing.")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=NOTEBOOKLM_TOKEN_LIMIT)
    parser.add_argument("--focus", type=str, default=None, help="Filter code files by path substring.")
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--data-dir", type=str, default=None, help="Path to data/ directory (default: auto-detect)")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else OUTPUT_FILE
    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR

    parts = []
    code_stats = {"files": 0, "skipped": 0, "truncated": 0, "original_lines": 0}

    print(f"\nExporting in '{args.mode}' mode...")

    if args.mode in ("code", "full"):
        print("\n[Code export]")
        code_body, code_stats = export_code(data_dir, verbose=args.verbose, focus=args.focus)
        parts.append(code_body)

    if args.mode in ("research", "full"):
        print("\n[Research data export]")
        research_body = export_research_data(data_dir, verbose=args.verbose)
        parts.append(research_body)

    body = "\n\n---\n\n".join(parts)
    token_estimate = estimate_tokens(body)
    preamble = build_preamble(args.mode, code_stats, token_estimate, args.max_tokens, data_dir)
    full_output = preamble + body

    final_tokens = estimate_tokens(full_output)
    size_mb = len(full_output.encode("utf-8")) / 1024 / 1024

    print(f"\n{'═' * 55}")
    print(f"  NotebookLM Export — {args.mode} mode")
    print(f"{'═' * 55}")
    if args.mode in ("code", "full"):
        print(f"  Code files:        {code_stats['files']}")
        print(f"  Truncated:         {code_stats['truncated']}")
    print(f"  Output size:       {size_mb:.2f} MB")
    print(f"  Est. tokens:       {final_tokens:,} / {args.max_tokens:,}")

    if final_tokens > args.max_tokens:
        print(f"  ⚠️  OVER BUDGET — use --focus or split into separate exports")
    else:
        print(f"  ✅ Within budget ({args.max_tokens - final_tokens:,} tokens remaining)")
    print(f"{'═' * 55}\n")

    if args.dry_run:
        print("Dry run — no file written.")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_output)
    print(f"✅ Written to {output_path}")
    if args.mode == "research":
        print("   Upload to NotebookLM to ask questions about RIT faculty and research areas.")
    elif args.mode == "full":
        print("   Upload to NotebookLM for both architectural and research Q&A.")


if __name__ == "__main__":
    main()
