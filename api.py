import os
import sys
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add src to python path to resolve local imports correctly
sys.path.append(os.getcwd())

from src.database import get_vector_store
from src.database.vector_store import process_data_into_documents
from src.database.models import Idea
from src.database.database import ResearchDatabase
from src.chatbot.ollama_client import get_ollama_client
from src.utils.config import FULL_CONFIG, RESTRICTED_CONFIG, DATA_DIR, ALLOWED_ORIGINS

# Use RESTRICTED_CONFIG when full data hasn't been crawled yet.
# Switch to FULL_CONFIG by setting API_MODE=full in .env.
import os as _os
_API_CONFIG = FULL_CONFIG if _os.getenv("API_MODE", "restricted") == "full" else RESTRICTED_CONFIG
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.synthesizer import ResponseSynthesizer
from src.collaboration.matcher import IdeaMatcher
from src.analysis.impact_analyzer import ImpactAnalyzer
from src.memory.session_store import MemoryModule
from src.utils.hardware import HW_PROFILE

# ---------------------------------------------------------------------------
# Global service instances (populated in lifespan)
# ---------------------------------------------------------------------------
retriever: Optional[HybridRetriever] = None
synthesizer: Optional[ResponseSynthesizer] = None
client: Optional[Any] = None
idea_matcher: Optional[IdeaMatcher] = None
impact_analyzer: Optional[ImpactAnalyzer] = None
memory: Optional[MemoryModule] = None
db: Optional[ResearchDatabase] = None


# ---------------------------------------------------------------------------
# B2 fix: lifespan context manager replaces deprecated @app.on_event("startup")
# FastAPI ≥ 0.93 standard pattern.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown all heavyweight resources."""
    global retriever, synthesizer, client, idea_matcher, impact_analyzer, memory, db

    print(f"[TigerResearchBuddy] Initializing services... (platform: {HW_PROFILE.platform})")

    # Init Vector Store
    store = get_vector_store(_API_CONFIG)
    store.initialize()

    # Init Ollama (B3: semaphore concurrency is set inside OllamaClient via HW_PROFILE)
    client = get_ollama_client()
    client.initialize()

    # Build BM25 index covering all three document types stored in ChromaDB:
    # (1) faculty/research_area/publication docs from main data JSON
    # (2) paper chunks from papers metadata JSONs
    # (3) research cards from research_cards JSONs
    import hashlib
    bm25_docs = []
    if _API_CONFIG.OUTPUT_FILE.exists():
        with open(_API_CONFIG.OUTPUT_FILE) as _f:
            _data = json.load(_f)
        bm25_docs.extend(process_data_into_documents(_data))
        print(f"[TigerResearchBuddy] BM25: loaded {len(bm25_docs)} faculty/area docs.")
    else:
        print(f"[TigerResearchBuddy] WARNING: {_API_CONFIG.OUTPUT_FILE} not found — faculty BM25 disabled.")

    # Add paper chunks — use same ID scheme as index_downloaded_papers so RRF can fuse with vector results
    _papers_dir = _API_CONFIG.PAPERS_DIR
    if _papers_dir.exists():
        _paper_count = 0
        for _pfile in _papers_dir.glob("*.json"):
            try:
                with open(_pfile) as _pf:
                    _paper = json.load(_pf)
                _title = _paper.get("title", "")
                if not _title:
                    continue
                _doc_id = f"paper_{hashlib.md5(_title.encode()).hexdigest()[:12]}"
                _authors = ", ".join(_paper.get("authors", [])[:5])
                _content = (
                    f"Research Paper: {_title}\n"
                    f"Authors: {_authors}\n"
                    f"Year: {_paper.get('year', 'Unknown')}\n"
                    f"Faculty: {_paper.get('faculty', '')}\n"
                    f"Abstract: {_paper.get('abstract', '')}\n"
                    f"Excerpt: {_paper.get('extracted_text', '')[:2000]}"
                )
                bm25_docs.append({
                    "id": f"{_doc_id}_chunk0",
                    "content": _content,
                    "metadata": {"doc_type": "paper", "title": _title, "authors": _authors},
                })
                _paper_count += 1
            except Exception:
                pass
        print(f"[TigerResearchBuddy] BM25: loaded {_paper_count} paper docs.")

    # Add research cards
    _cards_dir = _API_CONFIG.BASE_DIR / "research_cards"
    if _cards_dir.exists():
        _card_count = 0
        for _cfile in _cards_dir.glob("*.json"):
            try:
                with open(_cfile) as _cf:
                    _card = json.load(_cf)
                _card_id = str(_card.get("card_id", ""))
                if not _card_id:
                    continue
                _bib = _card.get("bibliographic_data", {})
                _core = _card.get("core_content", {})
                _kg = _card.get("knowledge_graph", {})
                _concepts = [
                    (n.get("label", "") if isinstance(n, dict) else n)
                    for n in _kg.get("nodes", [])
                ]
                _outcomes = _core.get("outcomes", [])
                if not isinstance(_outcomes, list):
                    _outcomes = [str(_outcomes)]

                # Extract RIT faculty and all authors from bibliographic data
                _raw_authors = _bib.get("authors", [])
                _rit_faculty = [
                    a["name"] for a in _raw_authors
                    if isinstance(a, dict) and a.get("affiliation") == "RIT" and a.get("name")
                ]
                _all_authors = [
                    (a["name"] if isinstance(a, dict) else str(a))
                    for a in _raw_authors[:8]
                ]

                _card_content = (
                    f"Title: {_bib.get('title', '')}\n"
                    f"RIT Faculty: {', '.join(_rit_faculty) if _rit_faculty else 'see authors'}\n"
                    f"Authors: {', '.join(_all_authors)}\n"
                    f"Year: {_bib.get('year', '')}\n"
                    f"Domain: {_bib.get('primary_domain', '')}\n"
                    f"Novelty: {_core.get('novelty_claim', '')}\n"
                    f"Methodology: {_core.get('key_methodology', '')}\n"
                    f"Outcomes: {', '.join(_outcomes)}\n"
                    f"Concepts: {', '.join(_concepts)}\n"
                    f"Abstract: {str(_core.get('full_text_markdown', ''))[:800]}"
                )
                _faculty_name = _rit_faculty[0] if _rit_faculty else ""
                bm25_docs.append({
                    "id": _card_id,
                    "content": _card_content,
                    "metadata": {
                        "doc_type": "research_card",
                        "title": _bib.get("title", ""),
                        "faculty": _faculty_name,
                        "rit_faculty": ", ".join(_rit_faculty),
                    },
                })
                _card_count += 1
            except Exception:
                pass
        print(f"[TigerResearchBuddy] BM25: loaded {_card_count} research card docs.")

    print(f"[TigerResearchBuddy] BM25 index: {len(bm25_docs)} total documents loaded.")

    # Create Retriever and Synthesizer
    retriever = HybridRetriever(vector_store=store, documents=bm25_docs if bm25_docs else None)
    synthesizer = ResponseSynthesizer()
    idea_matcher = IdeaMatcher()
    impact_analyzer = ImpactAnalyzer()

    # Session memory module (dual-tier: sliding window + optional LanceDB)
    memory = MemoryModule(HW_PROFILE)

    # Persistent chat history DB
    db = ResearchDatabase()

    print(
        f"[TigerResearchBuddy] Ready. "
        f"Concurrency: {HW_PROFILE.chat_concurrency} slot(s), "
        f"Context: {HW_PROFILE.context_window} tokens."
    )

    yield  # application runs here

    # Teardown (if needed in future: flush LanceDB, close connections, etc.)
    print("[TigerResearchBuddy] Shutting down.")


app = FastAPI(title="TigerResearchBuddy API", version="2.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS — ALLOWED_ORIGINS is read from env var, no more wildcard by default.
# Set ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com in .env
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # CORS hardening fix
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    use_cod: bool = False
    persona: str = "tiger"
    session_id: Optional[str] = None   # New: session-based memory routing


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    session_id: Optional[str] = None   # Echo back so frontend can persist it


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    """Chat endpoint with session-based conversational memory.

    Workflow:
    1. Look up (or create) the session's sliding-window history.
    2. Retrieve context via hybrid search with file locking.
    3. Inject history into the synthesizer prompt.
    4. Persist the new turn into the memory module.
    """
    if not retriever or not synthesizer or not client:
        raise HTTPException(status_code=500, detail="Backend services are off or initializing.")

    try:
        # Set Persona
        client.set_persona(request.persona)

        # Resolve or mint a session ID
        import uuid
        session_id = request.session_id or str(uuid.uuid4())

        # Load sliding-window history for this session
        history = memory.get_context_window(session_id) if memory else []

        # Retrieve context via hybrid search with file locking
        import filelock
        lock_path = DATA_DIR / ".pipeline.lock"
        try:
            with filelock.FileLock(lock_path, timeout=0):
                results = retriever.hybrid_search(request.query, k=7, rerank=False)
        except filelock.Timeout:
            raise HTTPException(
                status_code=503,
                detail="The research database is currently being updated. Please try again in a few moments.",
            )

        # Synthesize answer (history is now injected)
        final_answer = await synthesizer.synthesize_async(
            request.query, results, use_cod=request.use_cod, history=history
        )

        # Persist this turn to memory
        if memory:
            await memory.add_turn(session_id, "user", request.query)
            await memory.add_turn(session_id, "assistant", final_answer)

        # Clean up source references for JSON response
        clean_sources = [
            {
                "id": r.get("id"),
                "metadata": r.get("metadata", {}),
                "content": r.get("content", ""),
                "score": r.get("rrf_score", 0.0),
            }
            for r in results
        ]

        return ChatResponse(
            response=final_answer,
            sources=clean_sources,
            session_id=session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Streaming chat endpoint — disconnect-aware VRAM release
# ---------------------------------------------------------------------------

@app.post("/api/chat/stream")
async def handle_chat_stream(request: Request):
    """SSE streaming chat endpoint.

    Streams tokens via Server-Sent Events so the frontend displays
    responses in real-time.  The generator polls
    ``request.is_disconnected()`` on every token chunk — when the
    user clicks Stop (AbortController.abort()), the Ollama inference
    loop breaks immediately and releases the GPU VRAM.

    SSE protocol:
      data: [SOURCES]{json}\n\n      — retrieval results (first event)
      data: {token}\n\n             — each generated token
      data: [DONE]\n\n              — end of stream
    """
    if not retriever or not synthesizer or not client:
        raise HTTPException(status_code=500, detail="Backend services are off or initializing.")

    # Parse request body manually (can't use Pydantic model with Request)
    body = await request.json()
    query = body.get("query", "")
    persona = body.get("persona", "tiger")
    session_id = body.get("session_id")
    model_override = body.get("model", "auto")  # "auto" | specific model name

    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")

    client.set_persona(persona)

    import uuid
    session_id = session_id or str(uuid.uuid4())
    history = memory.get_context_window(session_id) if memory else []

    # Retrieve context (with file lock guard)
    import filelock
    from src.generation.synthesizer import _pick_model
    lock_path = DATA_DIR / ".pipeline.lock"
    try:
        with filelock.FileLock(lock_path, timeout=0):
            results = retriever.hybrid_search(query, k=7, rerank=False)
    except filelock.Timeout:
        raise HTTPException(
            status_code=503,
            detail="The research database is currently being updated. Please try again in a few moments.",
        )

    # Determine actual model
    actual_model = _pick_model(query, len(results)) if model_override == "auto" else model_override

    # Clean sources for the [SOURCES] SSE event
    clean_sources = [
        {
            "id": r.get("id"),
            "metadata": r.get("metadata", {}),
            "content": r.get("content", ""),
            "score": r.get("rrf_score", 0.0),
        }
        for r in results
    ]

    async def event_generator():
        # Emit pipeline step events so the frontend can show a "thinking" trace
        n_faculty = sum(1 for r in results if r.get("metadata", {}).get("doc_type") in ("professor", "faculty_profile"))
        n_papers = sum(1 for r in results if r.get("metadata", {}).get("doc_type") in ("publication", "paper", "research_paper", "research_card"))
        n_other = len(results) - n_faculty - n_papers
        source_summary = " · ".join(filter(None, [
            f"{n_faculty} faculty" if n_faculty else "",
            f"{n_papers} papers" if n_papers else "",
            f"{n_other} other" if n_other else "",
        ])) or "no matches"

        yield f"data: [STEP]{json.dumps({'step': 'retrieval', 'label': f'Retrieved {len(results)} sources', 'details': source_summary})}\n\n"
        yield f"data: [STEP]{json.dumps({'step': 'generate', 'label': f'Generating with {actual_model}', 'details': f'Persona: {persona} · history: {len(history)} turns'})}\n\n"

        # Emit sources so the citation panel populates
        yield f"data: [SOURCES]{json.dumps({'sources': clean_sources, 'session_id': session_id})}\n\n"

        # Stream tokens from the synthesizer
        full_response = []
        async for token in synthesizer.synthesize_stream_async(
            query, results, history=history, request=request, model=actual_model,
        ):
            full_response.append(token)
            # SSE format: data: {payload}\n\n
            yield f"data: {json.dumps({'token': token})}\n\n"

        yield "data: [DONE]\n\n"

        # Persist to session memory + DB after stream completes
        import time as _time
        full_text = "".join(full_response)
        now_ms = int(_time.time() * 1000)
        if memory:
            await memory.add_turn(session_id, "user", query)
            await memory.add_turn(session_id, "assistant", full_text)
        if db:
            title = query[:80].strip()
            db.save_chat_session(session_id, title, type="chat", persona=persona)
            db.save_chat_message(session_id, "user", query, now_ms)
            db.save_chat_message(session_id, "assistant", full_text, now_ms + 1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering if proxied
        },
    )


# ---------------------------------------------------------------------------
# Graph data endpoint
# ---------------------------------------------------------------------------

@app.get("/api/graph")
def get_graph_data():
    """Returns the NetworkX JSON graph data exported by GraphBuilder."""
    graph_path = DATA_DIR / "tiger_brain.json"

    if not graph_path.exists():
        return {"nodes": [], "links": []}

    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Drop unknown-type edges — they're crawler artifacts and dominate the
        # payload (~127K of 140K links), making the response ~23 MB.
        known_types = {
            "AUTHORED", "COAUTHORED_WITH", "MENTIONS", "HAS_TOPIC",
            "RELATED_TO", "COMBINES_WITH", "USES", "SOLVES", "ANALYZES",
            "APPLIES_TO", "ENHANCES", "MEASURES", "INFLUENCES", "SUPPORTS",
        }
        data["links"] = [
            l for l in data.get("links", [])
            if (l.get("type") or "").upper() in known_types
        ]
        return data
    except Exception as e:
        print(f"Graph load error: {e}")
        raise HTTPException(status_code=500, detail="Could not load Graph Data")


# ---------------------------------------------------------------------------
# Idea endpoint
# ---------------------------------------------------------------------------

class IdeaRequest(BaseModel):
    title: str
    description: str
    college: str
    tags: str


@app.post("/api/idea")
async def handle_idea(request: IdeaRequest):
    if not idea_matcher or not impact_analyzer:
        raise HTTPException(status_code=500, detail="Idea analyzers initializing.")

    tags_list = [t.strip() for t in request.tags.split(",") if t.strip()]

    new_idea = Idea(
        title=request.title,
        description=request.description,
        author_name="Student/Faculty (You)",
        college=request.college,
        tags=tags_list,
    )

    matches = idea_matcher.match_idea(new_idea)
    impact = await impact_analyzer.analyze_impact_async(new_idea.title, new_idea.description)

    collabs = [
        {
            "id": c.get("id"),
            "score": c.get("rrf_score", 0),
            "metadata": c.get("metadata", {}),
            "content": c.get("content", ""),
        }
        for c in matches.get("collaborators", [])
    ]

    if db:
        db.save_collaboration(
            title=request.title,
            description=request.description,
            college=request.college,
            tags=request.tags,
            impact_score=impact.get("score", 0),
            impact_summary=impact.get("summary", ""),
            collaborators_json=json.dumps(collabs),
        )

    return {"impact": impact, "collaborators": collabs}


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------

@app.get("/api/sessions")
def list_sessions(type: str = "chat", limit: int = 40):
    if not db:
        return []
    return db.get_sessions(type=type, limit=limit)


@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="DB not ready")
    return db.get_session_messages(session_id)


@app.get("/api/collaborations")
def list_collaborations(limit: int = 30):
    if not db:
        return []
    return db.get_collaborations(limit=limit)


@app.delete("/api/chat/{session_id}")
async def clear_session(session_id: str):
    if memory:
        memory.clear_session(session_id)
    if db:
        db.delete_session(session_id)
    return {"status": "cleared", "session_id": session_id}
