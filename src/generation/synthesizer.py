import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from ..chatbot.ollama_client import get_ollama_client
from ..utils.json_utils import extract_json  # B4: replaces all string surgery
from ..utils.config import LLMConfig

console = Console()

# Signals that a query needs deep synthesis — route to the large model
_COMPLEX_PATTERNS = re.compile(
    r"\b(compare|contrast|synthesize|summarize all|explain why|how does|what is the difference"
    r"|across|trend|overview|landscape|relate|connection between|impact of|implications"
    r"|in depth|deep dive|comprehensive|multiple|several|various)\b",
    re.IGNORECASE,
)

def _pick_model(query: str, n_results: int) -> str:
    """Route to fast or capable model based on query complexity."""
    is_complex = (
        len(query.split()) > 15
        or n_results > 5
        or _COMPLEX_PATTERNS.search(query) is not None
    )
    return LLMConfig.COMPLEX_MODEL if is_complex else LLMConfig.FAST_MODEL

# Pure greetings/chitchat — short-circuit before RAG
_GREETING_PATTERNS = re.compile(
    r"^\s*(hi+|hey+|hello|howdy|sup|what'?s up|good (morning|afternoon|evening)|greetings"
    r"|how are you|how('?re| are) (you|things)"
    r"|thanks|thank you|thx|bye|goodbye|cool|ok|okay|got it|nice"
    r"|test|testing|ping|hello there|yo)\s*[!?.]*\s*$",
    re.IGNORECASE,
)

# Meta/identity queries — let through to LLM so role.md handles them
_CONVERSATIONAL_PATTERNS = re.compile(
    r"^\s*(hi+|hey+|hello|howdy|sup|what'?s up|good (morning|afternoon|evening)|greetings"
    r"|how are you|how('?re| are) (you|things)|what (are|can) (you|u) do"
    r"|what are (your?|you) (capabilities?|features?|functions?|skills?|abilities?)"
    r"|what('?s| is) (your|this|tigerbrain|tigerresearch|tiger research)"
    r"|who are you|tell me about (yourself|you)|your? capabilities|what can (you|i)"
    r"|help me|can you help|what do you (know|do)|are you (an |a )?ai"
    r"|thanks|thank you|thx|bye|goodbye|cool|ok|okay|got it|nice"
    r"|test|testing|ping|hello there|yo)\s*[!?.]*\s*$",
    re.IGNORECASE,
)

_CAPABILITIES_RESPONSE = """Hi! I'm **TigerResearchBuddy** — an AI research advisor built for RIT students.

Here's what I can do:

**🔍 Find Research Opportunities**
Ask me about any topic and I'll surface relevant RIT faculty, their papers, and active research areas. Example: *"Who works on machine learning at RIT?"*

**👥 Discover Faculty**
I can match you with professors based on your interests and explain why they're relevant to you. Example: *"Find me someone working on computer vision for medical imaging."*

**🤝 Collaboration Hub**
Post a research idea and I'll find faculty whose work aligns with it, plus score your idea's potential impact.

**🧠 Knowledge Graph**
Explore a visual map of how RIT faculty, papers, and research concepts are connected.

**💬 Conversational Memory**
I remember our conversation — you can ask follow-up questions and I'll keep context.

What research area are you interested in exploring?"""

def _build_user_prompt(query: str, context_str: str, history_prefix: str = "") -> str:
    """Shared prompt used by all synthesis paths."""
    return f"""
TASK INSTRUCTIONS:
Your goal is to help students navigate research opportunities at RIT by connecting them with the right faculty and labs.
You MUST cite every factual claim with square-bracket source IDs like [1], [2].

IMPORTANT — how to use the context:
- Context entries may be FACULTY PROFILES, RESEARCH PAPERS, or RESEARCH CARDS.
- RESEARCH CARDS contain a "RIT Faculty:" field that names the professor(s) who authored or supervised that work.
  Use this field to answer questions about which professors work on a topic.
- If no direct faculty profile is available but research cards list RIT Faculty names, use those names to answer.
- Only say you cannot find information if the context genuinely contains nothing relevant to the query.
- NEVER invent names, titles, or research details not present in the context.

{history_prefix}Query: "{query}"

Context from RIT Database:
{context_str}

Task: Write a helpful, structured response for the student.
Format:

1. **Direct Answer**: One-paragraph summary answering the query directly.
2. **Key Faculty & Researchers**: For each relevant professor found in context:
   - **Name** [Source ID] — their role/title if known
   - **Focus**: What they work on (from their papers or bio).
   - **Representative work**: Specific paper titles or findings from context.
   - **Why relevant**: How their work connects to the query.
3. **Active Research Themes**: Group the retrieved papers into 2–3 thematic clusters.
4. **Recommended Next Step**: Concrete advice (e.g., "Email Prof X", "Read paper Y").

If the context truly has no relevant information, say so briefly — do not fabricate.

Response:
"""


class ResponseSynthesizer:
    """
    Synthesizes answers from retrieved context using local LLM.
    Enforces strict citation of sources.
    """
    
    def __init__(self, model_name: str = "tigerbuddy:latest"):
        self.client = get_ollama_client()
        self.model_name = model_name

    def synthesize(self, query: str, results: List[Dict], use_cod: bool = False) -> str:
        """
        Generate a cited response based on hybrid retrieval results.
        Args:
            query: User's question
            results: List of retrieved documents (RRF ranked)
            use_cod: If True, use Chain of Density prompting for deeper answers
        """
        if _GREETING_PATTERNS.match(query):
            return "Hey! How can I help you explore RIT research today?"

        context_str, sources = self._format_context(results)
        is_low_relevance = not results or all(r.get("rrf_score", 0) < 0.02 for r in results)

        if not context_str and not is_low_relevance:
            return "I couldn't find any relevant research or faculty in the database to answer that."

        if use_cod:
            return self._synthesize_cod(query, context_str, sources)

        # Standard Synthesis (Default)
        # Fix 4: Clean prompt layering — system_prompt is ONLY the persona voice.
        # All task instructions go into the user_prompt to avoid persona conflict.
        persona_system_prompt = (
            self.client._load_persona_prompt()
            if hasattr(self.client, '_load_persona_prompt')
            else "You are a helpful academic advisor."
        )

        user_prompt = _build_user_prompt(query, context_str)

        try:
            # Use generate for strict instruction following
            response = self.client.generate(
                prompt=user_prompt,
                system_prompt=persona_system_prompt
            )
            
            return self._format_output(response, sources)
            
        except Exception as e:
            console.print(f"[red]Synthesis failed: {e}[/]")
            return "Sorry, I encountered an error while generating the response."

    def _synthesize_cod(self, query: str, context_str: str, sources: List[Dict]) -> str:
        """
        Use Chain of Density prompting for a dense, high-quality answer.
        """
        console.print("[cyan]🧬 Using Chain of Density Synthesis...[/]")
        
        # Load CoD Prompt
        try:
            prompt_path = Path("data/prompts/chain_of_density.md")
            if prompt_path.exists():
                cod_template = prompt_path.read_text()
            else:
                cod_template = "You are an expert synthesizer. output json. {context_str}"
        except Exception as e:
             console.print(f"[red]Failed to load CoD prompt: {e}[/]")
             return self.synthesize(query, [], use_cod=False)

        # Replace placeholders
        user_prompt = cod_template.replace("{query}", query).replace("{context_str}", context_str)
        
        # Generate
        try:
            raw_response = self.client.generate(
                prompt=user_prompt,
                system_prompt="You are a JSON-speaking synthesis engine."
            )
            
            # B4 fix: use extract_json() — no string surgery
            data = extract_json(raw_response)
            if data:
                final_answer = data.get("final_answer", raw_response)
                added_entities = data.get("missing_entities_added", [])
                if added_entities and isinstance(added_entities, list):
                    final_answer += f"\n\n**🧬 Density Added:** {', '.join(added_entities)}"
            else:
                console.print("[yellow]Warning: CoD returned invalid JSON, using raw text.[/]")
                final_answer = raw_response

            return self._format_output(final_answer, sources)

        except Exception as e:
             console.print(f"[red]CoD Synthesis failed: {e}[/]")
             return f"Error in Deep Synthesis: {str(e)}"

    async def synthesize_async(
        self,
        query: str,
        results: List[Dict],
        use_cod: bool = False,
        history: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate a cited response with optional conversation history injection.

        Args:
            history: List of prior turn dicts [{"role": ..., "content": ...}]
                     from MemoryModule.get_context_window(). When provided,
                     the last N turns are prepended to the user prompt so the
                     LLM has conversational context.
        """
        if _GREETING_PATTERNS.match(query):
            return "Hey! How can I help you explore RIT research today?"

        context_str, sources = self._format_context(results)
        is_low_relevance = not results or all(r.get("rrf_score", 0) < 0.02 for r in results)

        if not context_str and not is_low_relevance:
            return "I couldn't find any relevant research or faculty in the database to answer that."

        if use_cod:
            return await self._synthesize_cod_async(query, context_str, sources)

        # Standard Synthesis (Default)
        # Fix 4: Clean prompt layering — system_prompt is ONLY the persona voice.
        persona_system_prompt = (
            self.client._load_persona_prompt()
            if hasattr(self.client, '_load_persona_prompt')
            else "You are a helpful academic advisor."
        )

        # Build conversation history prefix so the LLM has multi-turn context
        history_prefix = ""
        if history:
            history_prefix = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in history
            )
            history_prefix = f"\n--- Conversation History ---\n{history_prefix}\n--- End History ---\n\n"

        user_prompt = _build_user_prompt(query, context_str, history_prefix)

        try:
            response = await self.client.generate_async(
                prompt=user_prompt,
                system_prompt=persona_system_prompt,
                model=_pick_model(query, len(results)),
            )

            return self._format_output(response, sources)
            
        except Exception as e:
            console.print(f"[red]Synthesis async failed: {e}[/]")
            return "Sorry, I encountered an error while generating the response."

    async def synthesize_stream_async(
        self,
        query: str,
        results: List[Dict],
        history: Optional[List[Dict]] = None,
        request=None,
        model: Optional[str] = None,
    ):
        """Streaming synthesis — yields token chunks for SSE.

        Builds the same prompt as ``synthesize_async`` but delegates to
        ``client.generate_stream_async()`` which polls
        ``request.is_disconnected()`` on every chunk to release VRAM
        when the frontend aborts.

        Parameters
        ----------
        request : starlette.requests.Request, optional
            Passed through to the streaming generator for disconnect detection.
        """
        if _GREETING_PATTERNS.match(query):
            yield "Hey! How can I help you explore RIT research today?"
            return

        sources = self._format_sources(results)
        context_str = self._build_context_string(results, sources)
        is_low_relevance = not results or all(r.get("rrf_score", 0) < 0.02 for r in results)

        if not context_str and not is_low_relevance:
            yield "I couldn't find any relevant research or faculty in the database to answer that."
            return

        # Build prompt (identical to synthesize_async)
        persona_system_prompt = (
            self.client._load_persona_prompt()
            if hasattr(self.client, '_load_persona_prompt')
            else "You are a helpful academic advisor."
        )

        history_prefix = ""
        if history:
            history_prefix = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in history
            )
            history_prefix = f"\n--- Conversation History ---\n{history_prefix}\n--- End History ---\n\n"

        user_prompt = _build_user_prompt(query, context_str, history_prefix)

        try:
            async for token in self.client.generate_stream_async(
                prompt=user_prompt,
                system_prompt=persona_system_prompt,
                request=request,
                model=model if model else _pick_model(query, len(results)),
            ):
                yield token
        except Exception as e:
            console.print(f"[red]Stream synthesis failed: {e}[/]")
            yield f"\n\n⚠️ Error: {str(e)}"

    async def _synthesize_cod_async(self, query: str, context_str: str, sources: List[Dict]) -> str:
        console.print("[cyan]🧬 Using Async Chain of Density Synthesis...[/]")
        
        try:
            prompt_path = Path("data/prompts/chain_of_density.md")
            if prompt_path.exists():
                cod_template = prompt_path.read_text()
            else:
                cod_template = "You are an expert synthesizer. output json. {context_str}"
        except Exception as e:
             console.print(f"[red]Failed to load CoD prompt: {e}[/]")
             return await self.synthesize_async(query, [], use_cod=False)

        user_prompt = cod_template.replace("{query}", query).replace("{context_str}", context_str)
        
        try:
            raw_response = await self.client.generate_async(
                prompt=user_prompt,
                system_prompt="You are a JSON-speaking synthesis engine."
            )
            
            # B4 fix: use extract_json() — no string surgery
            data = extract_json(raw_response)
            if data:
                final_answer = data.get("final_answer", raw_response)
                added_entities = data.get("missing_entities_added", [])
                if added_entities and isinstance(added_entities, list):
                    final_answer += f"\n\n**🧬 Density Added:** {', '.join(added_entities)}"
            else:
                console.print("[yellow]Warning: CoD returned invalid JSON, using raw text.[/]")
                final_answer = raw_response

            return self._format_output(final_answer, sources)

        except Exception as e:
             console.print(f"[red]CoD Async Synthesis failed: {e}[/]")
             return f"Error in Deep Synthesis: {str(e)}"

    def _format_context(self, results: List[Dict]) -> tuple[str, List[Dict]]:
        """
        Format retrieved documents into a context string.
        """
        sources = []
        context_parts = []
        seen_ids = set()
        
        for doc in results:
            doc_id = doc.get('id', '')
            if doc_id in seen_ids: continue
            
            sources.append(doc)
            seen_ids.add(doc_id)
            
            i = len(sources)
            meta = doc.get('metadata', {})
            source_type = meta.get('doc_type', 'unknown')
            
            # Format based on type
            content = doc.get('content', '')
            if source_type in ['professor', 'faculty_profile']:
                context_entry = f"[{i}] FACULTY PROFILE: {content}"
            elif source_type in ['publication', 'research_paper', 'paper']:
                context_entry = f"[{i}] RESEARCH PAPER: {content}"
            elif source_type == 'research_card':
                context_entry = f"[{i}] RESEARCH CARD (distilled paper): {content}"
            else:
                context_entry = f"[{i}] SOURCE ({source_type}): {content[:1000].replace(chr(10), ' ')}"
            
            context_parts.append(context_entry)
            
        return "\n\n".join(context_parts), sources

    def _format_sources(self, results: List[Dict]) -> List[Dict]:
        """Extract deduplicated source documents from retrieval results."""
        sources = []
        seen_ids = set()
        for doc in results:
            doc_id = doc.get('id', '')
            if doc_id in seen_ids:
                continue
            sources.append(doc)
            seen_ids.add(doc_id)
        return sources

    def _build_context_string(self, results: List[Dict], sources: List[Dict]) -> str:
        """Build a numbered context string from sources for LLM prompt injection."""
        context_parts = []
        for i, doc in enumerate(sources, 1):
            meta = doc.get('metadata', {})
            source_type = meta.get('doc_type', 'unknown')
            content = doc.get('content', '')

            if source_type in ['professor', 'faculty_profile']:
                context_parts.append(f"[{i}] FACULTY PROFILE: {content}")
            elif source_type in ['publication', 'research_paper', 'paper']:
                context_parts.append(f"[{i}] RESEARCH PAPER: {content}")
            elif source_type == 'research_card':
                context_parts.append(f"[{i}] RESEARCH CARD (distilled paper): {content}")
            else:
                context_parts.append(f"[{i}] SOURCE ({source_type}): {content[:1000].replace(chr(10), ' ')}")

        return "\n\n".join(context_parts)

    def _format_output(self, response: str, sources: List[Dict]) -> str:
        """
        Return the generated response.
        (Sources are now handled cleanly by the frontend UI)
        """
        return response
