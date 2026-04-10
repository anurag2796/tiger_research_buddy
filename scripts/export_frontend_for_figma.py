"""
Export frontend code + design context to a single file optimized for Figma AI.

This produces a dump that gives a designer or Figma AI everything needed to
understand and improve the UI/UX without drowning them in backend RAG logic.

Includes:
  1. Product overview & feature summary (what the app does)
  2. Design system tokens — colors, fonts, spacing, component patterns
  3. All frontend source code (Next.js pages, components, CSS)
  4. API contract — endpoint schemas so Figma knows what data flows in/out
  5. The existing Streamlit UI code — for legacy design reference
  6. LLM persona definitions — so the designer understands tone/voice

Excludes:
  - All backend ML/RAG/pipeline/crawler/database code
  - Tests, scripts, experiments, legacy non-UI code
  - Data files, knowledge graphs, embeddings
"""

import os
from pathlib import Path
from typing import Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "frontend_dump_for_figma.txt"


# ─────────────────────────────────────────────────────────────────────────────
# PREAMBLE — Product & design context for the designer / Figma AI
# ─────────────────────────────────────────────────────────────────────────────
PREAMBLE = """\
# TigerResearchBuddy — Frontend Design Reference

This document contains everything a designer needs to understand and improve
the frontend of **TigerResearchBuddy**, an AI-powered research discovery platform
for Rochester Institute of Technology (RIT).

---

## Product Overview

TigerResearchBuddy helps RIT students and faculty:
- **Discover research** — search across Computing, Engineering, Science colleges
- **Chat with an AI** — ask questions about faculty, papers, and research areas
- **Find collaborators** — submit a research idea, get matched to faculty experts
- **Visualize connections** — explore a "TigerBrain" knowledge graph of research links
- **Analyze impact** — get UN Sustainable Development Goal (SDG) alignment scores

## Target Users
- RIT undergraduate and graduate students looking for research opportunities
- Faculty seeking interdisciplinary collaborators
- PhD students exploring the research landscape

## Current UI Stack
- **Next.js 16** with React 19 and TypeScript
- **Tailwind CSS v4** for styling
- **Framer Motion** for animations
- **Lucide React** for iconography
- **react-force-graph-2d** for knowledge graph visualization
- **Axios** for API calls to FastAPI backend on localhost:8000

## Three Main Views (Tabs)

### 1. 💬 Chat (Default)
- Full-screen AI chat interface with message bubbles
- Collapsible citation/source panel on the right
- Persona selector (Tiger 🐅 / Analyzer 📊 / Critique 🔍)
- Stop generation button, clear chat, auto-scroll

### 2. 💡 Collaboration Hub
- Left panel: form to submit a research idea (title, college, tags, description)
- Right panel: results showing Impact Score, SDG alignment, and matched faculty
- Faculty cards with name, college, relevance %, and expertise snippet

### 3. 🕸️ Prism View (Graph)
- Interactive force-directed graph of Faculty ↔ Papers ↔ Concepts
- Nodes color-coded by type, click to inspect
- Data loaded from /api/graph endpoint

---

## Design System — Current Tokens

### Color Palette
| Token            | Value                   | Usage                        |
|------------------|-------------------------|------------------------------|
| Background       | `#050505`               | App background (near-black)  |
| Foreground       | `#ededed`               | Default text                 |
| Neon Blue        | `#4ec5f1`               | Primary accent, bot avatar, borders, links |
| Neon Yellow      | `#ffe81f`               | Secondary accent, user avatar, bold text, highlights |
| Neon Red         | `#ff0055`               | Prism View tab accent        |
| Card BG          | `#111111`               | Component backgrounds        |
| Card Border      | `rgba(255,255,255,0.1)` | Subtle borders               |
| Input BG         | `#1a1a1a`               | Text input fields            |
| Hover Border     | `rgba(255,255,255,0.3)` | Hover state borders          |
| User Bubble      | `rgba(255,255,255,0.1)` | User message background      |
| Bot Bubble       | `rgba(0,0,0,0.4)`       | Bot message background       |
| Bot Bubble Border| `rgba(78,197,241,0.3)`  | Bot message border glow      |

### Typography
| Element     | Font          | Weight | Notes                  |
|-------------|---------------|--------|------------------------|
| Sans        | Geist Sans    | 400    | Body text via next/font |
| Mono        | Geist Mono    | 400    | Code/terminal elements  |
| Headings    | Geist Sans    | 700    | Bold, gradient optional |
| Brand Title | —             | Bold   | Gradient: blue → yellow |

### Spacing & Layout
- Full viewport height app (`h-screen`) with overflow hidden
- 4px base padding (`p-4`)
- 16px gap between chat and citation panel
- Rounded corners: `rounded-xl` (cards), `rounded-full` (inputs, avatars)
- `backdrop-blur-xl` for glassmorphism effect on cards

### Component Patterns
- **Message Bubbles**: rounded-2xl, with rounded-tr-sm (user) or rounded-tl-sm (bot)
- **Avatar**: 8×8 rounded-full with icon centered
- **Buttons**: rounded-full with hover glow (`shadow-[0_0_10px...]`)
- **Inputs**: rounded-full with focus glow effect
- **Tabs**: pill-style nav in header bar with active state bg tint
- **Citations Panel**: collapsible sidebar, 12px collapsed / 1/3 width expanded
- **Form Labels**: uppercase, tracking-widest, 60% opacity white, text-xs

---

## Legacy Streamlit Design (Star Wars Theme)

The original Streamlit app uses a Star Wars-inspired theme:
- Font: Orbitron (headings) + Roboto (body)
- Neon glow text shadows on headings
- HUD-style card backgrounds with blur
- User messages: yellow left border (Rebel Alliance)
- Bot messages: blue left border (Jedi Archive)
- Square-cornered buttons with yellow border → yellow fill on hover

The Next.js frontend is a modernized evolution of this theme, keeping the
dark space aesthetic and blue/yellow palette but moving to cleaner rounded
components and Tailwind utility classes.

---

## API Contract (Backend Endpoints)

The frontend talks to a FastAPI backend. Here are the endpoints and their
request/response shapes — important for understanding data flow into components.

### POST /api/chat
**Request:**
```json
{
  "query": "Who works on machine learning?",
  "use_cod": false,
  "persona": "tiger"
}
```
**Response:**
```json
{
  "response": "Based on the data, **Professor Zhao** works on...",
  "sources": [
    {
      "id": "doc_123",
      "metadata": {
        "doc_type": "professor",
        "name": "Weijie Zhao",
        "college": "Computing",
        "email": "wz@rit.edu"
      },
      "content": "Professor Zhao covers practical ML systems...",
      "score": 0.85
    }
  ]
}
```

### POST /api/idea
**Request:**
```json
{
  "title": "AI for Sustainable Farming",
  "description": "Using computer vision to optimize crop yields...",
  "college": "Computing",
  "tags": "ai, sustainability, agriculture"
}
```
**Response:**
```json
{
  "impact": {
    "score": 8,
    "summary": "Strong alignment with SDG 2 (Zero Hunger)...",
    "sdgs": ["SDG 2: Zero Hunger", "SDG 13: Climate Action"]
  },
  "collaborators": [
    {
      "id": "prof_456",
      "score": 0.72,
      "metadata": {"name": "Dr. Smith", "college": "Computing"},
      "content": "Research in computer vision and precision agriculture..."
    }
  ]
}
```

### GET /api/graph
**Response:** NetworkX JSON format
```json
{
  "nodes": [
    {"id": "prof_1", "label": "Dr. Kanan", "type": "faculty", "color": "#4ec5f1"},
    {"id": "paper_1", "label": "Zero-Shot Learning", "type": "paper", "color": "#ffe81f"}
  ],
  "links": [
    {"source": "prof_1", "target": "paper_1", "type": "AUTHORED_BY"}
  ]
}
```

---

## AI Personas (Affect UI Tone)

The chatbot has 3 personas that change the response style. The UI should
reflect which persona is active:

| Persona   | Icon | Accent Color | Response Style                     |
|-----------|------|--------------|-------------------------------------|
| Tiger 🐅  | 🐅   | `#4ec5f1`    | Friendly, encouraging, approachable |
| Analyzer 📊| 📊   | `#4ec5f1`    | Technical, data-focused, precise   |
| Critique 🔍| 🔍   | `#4ec5f1`    | Constructive, critical, thorough   |

---

## Source Code Follows

Below is every frontend source file, plus the API backend (api.py) and
the legacy Streamlit UI (web_app.py) for design reference.

---

"""


def get_lang(ext: str, filename: str) -> str:
    """Map file extension to code block language."""
    lang_map = {
        ".py": "python", ".tsx": "tsx", ".ts": "typescript",
        ".css": "css", ".json": "json", ".md": "markdown",
        ".toml": "toml", ".mjs": "javascript",
    }
    return lang_map.get(ext, "text")


def export_frontend():
    """Export frontend-focused dump."""
    # Files to include, in exact order
    files_to_include = [
        # ── Frontend source (Next.js) ──
        ("frontend/package.json", "Dependencies and scripts for the Next.js frontend"),
        ("frontend/next.config.ts", "Next.js configuration"),
        ("frontend/src/app/globals.css", "Global CSS — design tokens, scrollbar, prose styles"),
        ("frontend/src/app/layout.tsx", "Root layout — font loading, HTML shell"),
        ("frontend/src/app/page.tsx", "Main page — tab navigation, layout composition"),
        ("frontend/src/components/ChatInterface.tsx", "Chat component — messages, input, persona selector, streaming"),
        ("frontend/src/components/CitationPanel.tsx", "Citation sidebar — collapsible source viewer"),
        ("frontend/src/components/CollaborationHub.tsx", "Collaboration Hub — idea form + results with impact scores"),
        ("frontend/src/components/GraphViewer.tsx", "Graph Viewer — force-directed knowledge graph visualization"),

        # ── API Contract ──
        ("api.py", "FastAPI backend — endpoint definitions and data shapes"),

        # ── Legacy Streamlit UI (design reference) ──
        ("web_app.py", "Legacy Streamlit web app — Star Wars theme, chat, collaboration hub"),

        # ── LLM Persona Prompts (affect UX tone) ──
        ("data/prompts/role.md", "Base AI persona identity and behavior rules"),
        ("data/prompts/skills.md", "AI capabilities and response formatting instructions"),
        ("data/prompts/analyzer.md", "Analyzer persona — technical, data-focused mode"),
        ("data/prompts/critique.md", "Critique persona — constructive critical reviewer mode"),
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(PREAMBLE)

        for rel_path, description in files_to_include:
            file_path = ROOT_DIR / rel_path
            if not file_path.exists():
                out.write(f"## File: {rel_path}\n> ⚠️ File not found — may have been moved or renamed\n\n")
                continue

            ext = file_path.suffix.lower()
            lang = get_lang(ext, file_path.name)

            out.write(f"## File: {rel_path}\n")
            out.write(f"> {description}\n\n")

            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception as e:
                out.write(f"```\nError reading file: {e}\n```\n\n")
                continue

            out.write(f"```{lang}\n{content}\n```\n\n")

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ Generated {OUTPUT_FILE}")
    print(f"   Size: {size_kb:.1f} KB")
    print(f"   Files included: {len(files_to_include)}")


if __name__ == "__main__":
    export_frontend()
