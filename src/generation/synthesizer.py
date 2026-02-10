import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from ..chatbot.ollama_client import get_ollama_client

console = Console()

class ResponseSynthesizer:
    """
    Synthesizes answers from retrieved context using local LLM.
    Enforces strict citation of sources.
    """
    
    def __init__(self, model_name: str = "tigerbuddy:latest"):
        self.client = get_ollama_client()
        self.model_name = model_name

    def synthesize(self, query: str, results: Dict[str, Any], use_cod: bool = False) -> str:
        """
        Generate a cited response based on hybrid retrieval results.
        Args:
            query: User's question
            results: Dictionary of graph and vector results
            use_cod: If True, use Chain of Density prompting for deeper answers
        """
        context_str, sources = self._format_context(results)
        
        if not context_str:
            # Check if we have partial entity matches to suggest
            entities = results.get('entities', [])
            partial_matches = [e for e in entities if e.get('match_quality') == 'partial']
            
            if partial_matches:
                suggestions = [f"- **{e['label']}** ({e['type']})" for e in partial_matches[:5]]
                return (
                    f"I couldn't find an exact match for your query, but I found these similar topics/people:\n\n" + 
                    "\n".join(suggestions) + 
                    "\n\n**Did you mean one of these?**"
                )
            
            return "I couldn't find any relevant research or faculty in the database to answer that."

        if use_cod:
            return self._synthesize_cod(query, context_str, sources)

        # Standard Synthesis (Default)
        system_prompt = (
            "You are a knowledgeable Academic Advisor at RIT's Golisano College. "
            "Your goal is to help students navigate research opportunities by connecting them with the right faculty and labs. "
            "You speak in a helpful, professional, and encouraging tone. "
            "You MUST cite your sources using square brackets like [1], [2]."
        )

        user_prompt = f"""
Query: "{query}"

{self._get_ambiguity_note(results)}


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
- Do not hallucinate. Only use provided context.

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
             return self.synthesize(query, {"vector_results": [], "graph_results": []}, use_cod=False)

        # Replace placeholders
        user_prompt = cod_template.replace("{query}", query).replace("{context_str}", context_str)
        
        # Generate
        try:
            raw_response = self.client.generate(
                prompt=user_prompt,
                system_prompt="You are a JSON-speaking synthesis engine."
            )
            
            # Parse JSON
            # Clean potential markdown blocks
            clean_response = raw_response.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(clean_response)
                final_answer = data.get("final_answer", raw_response)
                # Append Missing Entities info if available, for transparency
                added_entities = data.get("missing_entities_added", [])
                if added_entities and isinstance(added_entities, list):
                    final_answer += f"\n\n**🧬 Density Added:** {', '.join(added_entities)}"
                    
            except json.JSONDecodeError:
                console.print("[yellow]Warning: CoD returned invalid JSON, using raw text.[/]")
                final_answer = raw_response

            return self._format_output(final_answer, sources)

        except Exception as e:
             console.print(f"[red]CoD Synthesis failed: {e}[/]")
             return f"Error in Deep Synthesis: {str(e)}"

    def _format_context(self, results: Dict[str, Any]) -> tuple[str, List[Dict]]:
        """
        Combine graph and vector results into a numbered context list.
        """
        sources = []
        context_parts = []
        seen_ids = set()
        
        # Helper to process doc
        def process_doc(doc):
            if doc['id'] in seen_ids: return
            sources.append(doc)
            seen_ids.add(doc['id'])
            
            i = len(sources)
            meta = doc.get('metadata', {})
            source_type = meta.get('type', 'unknown')
            
            # Format based on type
            if source_type == 'faculty_profile':
                # Rich faculty profile
                content = doc.get('text', '')
                context_entry = f"[{i}] FACULTY PROFILE: {content}"
            elif source_type == 'research_paper':
                # Paper with authors
                content = doc.get('text', '')
                source_node = meta.get('source_node', '')
                reason = f" [Relevant to: {source_node}]" if source_node else ""
                context_entry = f"[{i}] RESEARCH PAPER{reason}: {content}"
            else:
                # Generic fallback
                title = meta.get('title', doc.get('text', 'Source'))
                content = doc.get('text', '')[:500].replace('\n', ' ')
                context_entry = f"[{i}] {title} ({source_type}): {content}"
            
            context_parts.append(context_entry)

        # Prioritize Graph results (Faculty & Papers)
        for doc in results.get('graph_results', []):
            process_doc(doc)
        
        # Add Vector results (Global context)
        for doc in results.get('vector_results', []):
            process_doc(doc)
            
        return "\n\n".join(context_parts), sources

    def _format_output(self, response: str, sources: List[Dict]) -> str:
        """
        Append source details to the response.
        """
        output = [response, "\n\n**Sources:**"]
        
        for i, doc in enumerate(sources, 1):
            meta = doc.get('metadata', {})
            title = meta.get('title', doc.get('text', 'Source'))
            
            # If it's a paper, maybe show authors?
            # For now keep it simple
            output.append(f"[{i}] {title}")
            
        return "\n".join(output)

    def _get_ambiguity_note(self, results: Dict[str, Any]) -> str:
        """
        Check for partial/fuzzy matches and return a note for the LLM.
        """
        entities = results.get('entities', [])
        partial_matches = [e for e in entities if e.get('match_quality') == 'partial']
        
        if partial_matches:
            names = ", ".join([f"{e['label']} ({e['type']})" for e in partial_matches[:3]])
            return (
                f"NOTE: The user's query partially matched the following entities in our database: {names}.\n"
                "If the retrieved context is relevant to these entities, explicitly mention: 'Assuming you meant [Name]...' "
                "in your response."
            )
        return ""
