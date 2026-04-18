import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from ..chatbot.ollama_client import get_ollama_client
from ..utils.json_utils import extract_json  # B4: replaces all string surgery

console = Console()

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
        context_str, sources = self._format_context(results)
        
        if not context_str:
            # Smart fallback for empty context
            prompt = (
                f"User Query: '{query}'\n\n"
                "Task: Determine if the user is asking a conversational question (e.g., 'how are you', 'who are you', 'hello', 'what are you doing') "
                "or if they are asking a specific question requiring factual research or data.\n"
                "- If conversational: Respond naturally, politely, and concisely as TigerResearchBuddy, an AI academic advisor.\n"
                "- If it is a request for research, data, or faculty: Reply EXACTLY with this phrase: "
                "'I couldn't find any relevant research or faculty in the database to answer that.'"
            )
            try:
                fallback_response = self.client.generate(prompt, system_prompt="You are TigerResearchBuddy, a helpful academic AI assistant.")
                return fallback_response
            except Exception:
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

        user_prompt = f"""
TASK INSTRUCTIONS:
Your goal is to help students navigate research opportunities by connecting them with the right faculty and labs.
You MUST cite your sources using square brackets like [1], [2].
CRITICAL EXCEPTION: If the context provided does not contain RELEVANT information to answer the query,
you MUST state 'I could not find relevant information in the database to answer your query.' DO NOT hallucinate names or research areas.

Query: "{query}"

Context from RIT Database:
{context_str}

Task: Write a structured response for the student.
Follow this format EXACTLY:

1. **Direct Answer**: Brief summary of who/what addresses the query.
2. **Key Faculty & Researchers**: 
   - Name and Title [Source ID]
   - **Focus**: What they work on (inferred from papers/bio).
   - **Research**: Specific details from the context.
   - **Why relevant**: Connect their work to the user's query.
3. **Active Research Areas**: Group the retrieved papers into 2-3 themes.
4. **Recommended Next Step**: Actionable advice (e.g., "Read paper X", "Contact Prof Y").

Rules:
- Cite every claim with [x].
- If a faculty member is listed in context, use their full bio details.
- CRITICAL: Do not hallucinate. Do not output placeholder names like '[Name]'. If no relevant faculty or papers exist in the Context, ABORT the standard format and just say 'No relevant data found.'

Response:
"""
        
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
        context_str, sources = self._format_context(results)
        
        if not context_str:
            prompt = (
                f"User Query: '{query}'\n\n"
                "Task: Determine if the user is asking a conversational question (e.g., 'how are you', 'who are you', 'hello', 'what are you doing') "
                "or if they are asking a specific question requiring factual research or data.\n"
                "- If conversational: Respond naturally, politely, and concisely as TigerResearchBuddy, an AI academic advisor.\n"
                "- If it is a request for research, data, or faculty: Reply EXACTLY with this phrase: "
                "'I couldn't find any relevant research or faculty in the database to answer that.'"
            )
            try:
                fallback_response = await self.client.generate_async(prompt, system_prompt="You are TigerResearchBuddy, a helpful academic AI assistant.")
                return fallback_response
            except Exception:
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

        user_prompt = f"""
TASK INSTRUCTIONS:
Your goal is to help students navigate research opportunities by connecting them with the right faculty and labs.
You MUST cite your sources using square brackets like [1], [2].
CRITICAL EXCEPTION: If the context provided does not contain RELEVANT information to answer the query,
you MUST state 'I could not find relevant information in the database to answer your query.' DO NOT hallucinate names or research areas.

{history_prefix}Query: "{query}"

Context from RIT Database:
{context_str}

Task: Write a structured response for the student.
Follow this format EXACTLY:

1. **Direct Answer**: Brief summary of who/what addresses the query.
2. **Key Faculty & Researchers**: 
   - Name and Title [Source ID]
   - **Focus**: What they work on (inferred from papers/bio).
   - **Research**: Specific details from the context.
   - **Why relevant**: Connect their work to the user's query.
3. **Active Research Areas**: Group the retrieved papers into 2-3 themes.
4. **Recommended Next Step**: Actionable advice (e.g., "Read paper X", "Contact Prof Y").

Rules:
- Cite every claim with [x].
- If a faculty member is listed in context, use their full bio details.
- CRITICAL: Do not hallucinate. Do not output placeholder names like '[Name]'. If no relevant faculty or papers exist in the Context, ABORT the standard format and just say 'No relevant data found.'

Response:
"""
        
        try:
            response = await self.client.generate_async(
                prompt=user_prompt,
                system_prompt=persona_system_prompt
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
        sources = self._format_sources(results)
        context_str = self._build_context_string(results, sources)

        # No context → short-circuit with a fallback message
        if not results or context_str.strip() == "":
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

        user_prompt = f"""
TASK INSTRUCTIONS:
Your goal is to help students navigate research opportunities by connecting them with the right faculty and labs.
You MUST cite your sources using square brackets like [1], [2].
CRITICAL EXCEPTION: If the context provided does not contain RELEVANT information to answer the query,
you MUST state 'I could not find relevant information in the database to answer your query.' DO NOT hallucinate names or research areas.

{history_prefix}Query: "{query}"

Context from RIT Database:
{context_str}

Task: Write a structured response for the student.
Follow this format EXACTLY:

1. **Direct Answer**: Brief summary of who/what addresses the query.
2. **Key Faculty & Researchers**: 
   - Name and Title [Source ID]
   - **Focus**: What they work on (inferred from papers/bio).
   - **Research**: Specific details from the context.
   - **Why relevant**: Connect their work to the user's query.
3. **Active Research Areas**: Group the retrieved papers into 2-3 themes.
4. **Recommended Next Step**: Actionable advice (e.g., "Read paper X", "Contact Prof Y").

Rules:
- Cite every claim with [x].
- If a faculty member is listed in context, use their full bio details.
- CRITICAL: Do not hallucinate. Do not output placeholder names like '[Name]'. If no relevant faculty or papers exist in the Context, ABORT the standard format and just say 'No relevant data found.'

Response:
"""

        try:
            async for token in self.client.generate_stream_async(
                prompt=user_prompt,
                system_prompt=persona_system_prompt,
                request=request,
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
            if source_type in ['professor', 'faculty_profile']:
                content = doc.get('content', '')
                context_entry = f"[{i}] FACULTY PROFILE: {content}"
            elif source_type in ['publication', 'research_paper']:
                content = doc.get('content', '')
                context_entry = f"[{i}] RESEARCH PAPER: {content}"
            else:
                content = doc.get('content', '')[:1000].replace('\n', ' ')
                context_entry = f"[{i}] SOURCE ({source_type}): {content}"
            
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
            elif source_type in ['publication', 'research_paper']:
                context_parts.append(f"[{i}] RESEARCH PAPER: {content}")
            else:
                context_parts.append(f"[{i}] SOURCE ({source_type}): {content[:1000].replace(chr(10), ' ')}")

        return "\n\n".join(context_parts)

    def _format_output(self, response: str, sources: List[Dict]) -> str:
        """
        Return the generated response.
        (Sources are now handled cleanly by the frontend UI)
        """
        return response
