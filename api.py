import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to python path to resolve local imports correctly
sys.path.append(os.getcwd())

from src.database import get_vector_store
from src.database.models import Idea
from src.chatbot.ollama_client import get_ollama_client
from src.utils.config import FULL_CONFIG, DATA_DIR
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.synthesizer import ResponseSynthesizer
from src.collaboration.matcher import IdeaMatcher
from src.analysis.impact_analyzer import ImpactAnalyzer

app = FastAPI(title="TigerResearchBuddy API", version="2.0")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances mapped to endpoints
retriever: Optional[HybridRetriever] = None
synthesizer: Optional[ResponseSynthesizer] = None
client: Optional[Any] = None
idea_matcher: Optional[IdeaMatcher] = None
impact_analyzer: Optional[ImpactAnalyzer] = None

@app.on_event("startup")
def startup_event():
    """Initialize resources on startup."""
    global retriever, synthesizer, client, idea_matcher, impact_analyzer
    print("Initializing vector store and LLM clients...")
    
    # Init Vector Store
    store = get_vector_store(FULL_CONFIG)
    store.initialize()
    
    # Init Ollama
    client = get_ollama_client()
    client.initialize()
    
    # Create Retriever and Synthesizer
    retriever = HybridRetriever(vector_store=store)
    synthesizer = ResponseSynthesizer()
    idea_matcher = IdeaMatcher()
    impact_analyzer = ImpactAnalyzer()

class ChatRequest(BaseModel):
    query: str
    use_cod: bool = False
    persona: str = "tiger"

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]

@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    """Chat endpoint parsing user queries via Retriever and generating an LLM response."""
    if not retriever or not synthesizer or not client:
        raise HTTPException(status_code=500, detail="Backend services are off or initializing.")
        
    try:
        # Set Persona
        client.set_persona(request.persona)
        
        # Retrieve context via hybrid search with file locking to protect against concurrent DB rebuilds
        import filelock
        lock_path = DATA_DIR / ".pipeline.lock"
        try:
            with filelock.FileLock(lock_path, timeout=0):
                results = retriever.hybrid_search(request.query, k=7)
        except filelock.Timeout:
            raise HTTPException(status_code=503, detail="The research database is currently being updated. Please try again in a few moments.")
        
        # Synthesize final natural language answer
        final_answer = await synthesizer.synthesize_async(request.query, results, use_cod=request.use_cod)
        
        # Clean up source references for JSON response
        clean_sources = []
        for r in results:
            clean_sources.append({
                "id": r.get("id"),
                "metadata": r.get("metadata", {}),
                "content": r.get("content", ""),
                "score": r.get("rrf_score", 0.0)
            })
            
        return ChatResponse(response=final_answer, sources=clean_sources)
        
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph")
def get_graph_data():
    """Returns the NetworkX JSON graph data exported by GraphBuilder to feed the frontend."""
    graph_path = DATA_DIR / "tiger_brain.json"
    
    if not graph_path.exists():
        # Empty graph fallback
        return {"nodes": [], "links": []}
        
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Graph load error: {e}")
        raise HTTPException(status_code=500, detail="Could not load Graph Data")

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
        tags=tags_list
    )
    
    matches = idea_matcher.match_idea(new_idea)
    impact = await impact_analyzer.analyze_impact_async(new_idea.title, new_idea.description)
    
    # Just serialize collaborators for frontend
    collabs = []
    for c in matches.get("collaborators", []):
         collabs.append({
             "id": c.get("id"),
             "score": c.get("rrf_score", 0),
             "metadata": c.get("metadata", {}),
             "content": c.get("content", "")
         })
         
    return {
        "impact": impact,
        "collaborators": collabs
    }
