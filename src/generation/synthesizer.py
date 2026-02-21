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
             return self.synthesize(query, [], use_cod=False)

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
        Append source details to the response.
        """
        output = [response, "\n\n**Sources:**"]
        
        for i, doc in enumerate(sources, 1):
            meta = doc.get('metadata', {})
            # Use title if available, otherwise fallback
            title = meta.get('name') or meta.get('title') or doc.get('id')
            
            output.append(f"[{i}] {title}")
            
        return "\n".join(output)
