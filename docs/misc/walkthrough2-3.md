# Security & Architecture Fixes — Walkthrough

## Summary

Implemented 6 of 10 audit fixes (the other 4 were already done from previous work). All changes are syntax-verified and unit-tested.

---

## Changes Made

### Fix 4: Prompt Layering — Resolve Persona Conflict

**File:** [synthesizer.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/generation/synthesizer.py)

- **Before:** `system_prompt` = persona + task instructions concatenated. This overwrote the persona loaded by `OllamaClient._load_persona_prompt()` and conflicted with the Modelfile SYSTEM directive.
- **After:** `system_prompt` = **only** the persona voice/tone. All task instructions (citation rules, format spec, grounding rules) moved to `user_prompt`. Applied to both `synthesize()` and `synthesize_async()`.

```diff:synthesizer.py
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
        base_persona = self.client._load_persona_prompt() if hasattr(self.client, '_load_persona_prompt') else "You are a helpful academic advisor."
        
        system_prompt = (
            f"{base_persona}\n\n"
            "TASK INSTRUCTIONS:\n"
            "Your goal is to help students navigate research opportunities by connecting them with the right faculty and labs. "
            "You MUST cite your sources using square brackets like [1], [2]. "
            "CRITICAL EXCEPTION: If the context provided does not contain RELEVANT information to answer the query, "
            "you MUST state 'I could not find relevant information in the database to answer your query.' DO NOT hallucinate names or research areas."
        )

        user_prompt = f"""
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
                system_prompt=system_prompt
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
        base_persona = self.client._load_persona_prompt() if hasattr(self.client, '_load_persona_prompt') else "You are a helpful academic advisor."
        
        system_prompt = (
            f"{base_persona}\n\n"
            "TASK INSTRUCTIONS:\n"
            "Your goal is to help students navigate research opportunities by connecting them with the right faculty and labs. "
            "You MUST cite your sources using square brackets like [1], [2]. "
            "CRITICAL EXCEPTION: If the context provided does not contain RELEVANT information to answer the query, "
            "you MUST state 'I could not find relevant information in the database to answer your query.' DO NOT hallucinate names or research areas."
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
                system_prompt=system_prompt
            )
            
            return self._format_output(response, sources)
            
        except Exception as e:
            console.print(f"[red]Synthesis async failed: {e}[/]")
            return "Sorry, I encountered an error while generating the response."

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

    def _format_output(self, response: str, sources: List[Dict]) -> str:
        """
        Return the generated response.
        (Sources are now handled cleanly by the frontend UI)
        """
        return response
===
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

    def _format_output(self, response: str, sources: List[Dict]) -> str:
        """
        Return the generated response.
        (Sources are now handled cleanly by the frontend UI)
        """
        return response
```

---

### Fix 5: Thread-Safe Singleton Initialization

**Files:** [vector_store.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/database/vector_store.py), [ollama_client.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/chatbot/ollama_client.py), [gemini_client.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/chatbot/gemini_client.py)

- **Before:** Bare `if None: create()` pattern — two concurrent threads could both create instances, causing `sqlite3.OperationalError: database is locked` for ChromaDB.
- **After:** Double-checked locking with `threading.Lock()` on all three singletons.
- **Bonus:** Added `GeminiClient.generate_async()` using `run_in_threadpool`.

---

### Fix 6: NetworkX Graph File Locking + TTL Cache

**Files:** [query_engine.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/chatbot/query_engine.py), [graph_builder.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/knowledge_graph/graph_builder.py)

- **Before:** `_load_networkx_graph()` cached forever after first load. `GraphBuilder.export()` wrote to disk without locking. Concurrent pipeline rebuild + graph traversal → `RuntimeError: dictionary changed size during iteration`.
- **After:**
  - `_load_networkx_graph()` checks `os.path.getmtime()` against cached mtime — only re-reads when file changes.
  - Acquires `filelock.FileLock` before reading. On timeout (pipeline writing), returns stale cached graph.
  - `GraphBuilder.export()` wraps file write with the same `FileLock` for atomic writes.

---

### Fix 7: Impact Analyzer — Silent Failure → RuntimeError

**File:** [impact_analyzer.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/analysis/impact_analyzer.py)

- **Before:** Caught all exceptions and returned `{"score": 0}`, silently showing students a false zero-impact score.
- **After:**
  - Created Pydantic `ImpactSchema` (score, sdgs, summary) with validation.
  - `re.search(r'\{.*\}', response, re.DOTALL)` for JSON extraction.
  - Retry loop (max 2 attempts) with `options={"format": "json", "temperature": 0.1}`.
  - On final failure: **raises `RuntimeError`** → API returns HTTP 500.

---

### Fix 8: Keyword Extraction Fallback Coercion

**File:** [query_engine.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/chatbot/query_engine.py)

- **Before:** If LLM returned `"high_level_keywords": "deep learning"` (string instead of list), Pydantic threw `ValidationError` and the fallback injected the entire raw query as a BM25 term.
- **After:** Added `@field_validator('high_level_keywords', 'low_level_keywords', mode='before')` that:
  - Coerces bare strings to `["string"]`
  - Splits comma-separated strings: `"a, b, c"` → `["a", "b", "c"]`

---

### Fix 9: PDF Distiller Pipeline Fault Tolerance

**File:** [pdf_distiller.py](file:///Users/anurag/codebase/personalProjects/tiger_research_buddy/src/processors/pdf_distiller.py)

- **Before:** `JSONDecodeError` from a single malformed VLM response returned `None`, and while `return_exceptions=True` caught it, the card was silently lost.
- **After:** On JSON parse failure, returns a structured error card:
  ```python
  {"card_id": filename, "bibliographic_data": {"title": f"Failed: {filename}"},
   "core_content": {"error": reason}, "knowledge_graph": {"nodes": [], "edges": []}}
  ```
  The batch loop writes the error card to disk and continues — never crashes for a single-document failure.

---

## What Was Tested

| Check | Result |
|-------|--------|
| `py_compile` on all 9 files | ✓ All pass |
| Modelfile has no hardcoded `num_ctx`/`temperature` | ✓ Confirmed |
| No bare `ollama.chat()` in async code paths | ✓ Only in sync methods (correct) |
| All singletons use `threading.Lock` | ✓ Confirmed |
| `ImpactSchema` Pydantic validation | ✓ Validated |
| `KeywordExtractionSchema` string→list coercion | ✓ `"deep learning"` → `["deep learning"]` |
| `KeywordExtractionSchema` comma-split | ✓ `"ResNet-50, ImageNet"` → `["ResNet-50", "ImageNet"]` |
| Regex JSON extraction + ImpactSchema | ✓ Extracts from prose-wrapped output |

## Previously Implemented (No Changes Needed)

- **Fix 1**: Async wrappers (`generate_async`, `synthesize_async`) — already in place
- **Fix 2**: VRAM semaphore (`asyncio.Semaphore` in `generate_async`) — already in place
- **Fix 3**: Token math / Modelfile cleanup — already done
- **Fix 10**: File lock on `hybrid_search` in `api.py` — already in place
