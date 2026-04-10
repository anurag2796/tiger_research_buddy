from ..chatbot.ollama_client import get_ollama_client
import json

class ImpactAnalyzer:
    """Analyzes the potential impact of research ideas."""
    
    def __init__(self):
        self.client = get_ollama_client()
        
    def analyze_impact(self, title: str, description: str) -> dict:
        """
        Generates an impact score and SDG alignment.
        """
        if not self.client._initialized:
            self.client.initialize()
            
        prompt = f"""
        Analyze the following research idea for potential societal impact.
        Title: {title}
        Description: {description}
        
        Task:
        1. Assign an "Impact Score" from 1-10 (10 being high global impact).
        2. Identify relevant UN Sustainable Development Goals (SDGs).
        3. Write a 1-sentence summary of why it matters.
        
        Output JSON format ONLY:
        {{
            "score": 8.5,
            "sdgs": ["Goal 2: Zero Hunger", "Goal 13: Climate Action"],
            "summary": "This research addresses critical food security issues..."
        }}
        """
        
        try:
            response = self.client.generate(prompt, system_prompt="You are an impact analyst. Output JSON only.")
            
            # Robust JSON extraction
            try:
                # Try direct parse first in case it's clean
                return json.loads(response.strip())
            except json.JSONDecodeError:
                # Fallback to brace depth-tracking extraction
                start_idx = response.find("{")
                if start_idx != -1:
                    brace_count = 0
                    end_idx = -1
                    for i, char in enumerate(response[start_idx:]):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = start_idx + i
                                break
                    if end_idx != -1:
                        try:
                            return json.loads(response[start_idx:end_idx+1])
                        except json.JSONDecodeError:
                            print("Brace match found JSON object but could not be parsed.")
                
                print("Failed to find valid JSON in LLM response.")
                return {"score": 0, "sdgs": [], "summary": "Invalid JSON response from model.", "error": "parse_error"}
                
        except Exception as e:
            print(f"Impact analysis failed: {e}")
            return {"score": 0, "sdgs": [], "summary": "Could not analyze impact.", "error": str(e)}

    async def analyze_impact_async(self, title: str, description: str) -> dict:
        """
        Generates an impact score and SDG alignment asynchronously.
        """
        if not self.client._initialized:
            self.client.initialize()
            
        prompt = f"""
        Analyze the following research idea for potential societal impact.
        Title: {title}
        Description: {description}
        
        Task:
        1. Assign an "Impact Score" from 1-10 (10 being high global impact).
        2. Identify relevant UN Sustainable Development Goals (SDGs).
        3. Write a 1-sentence summary of why it matters.
        
        Output JSON format ONLY:
        {{
            "score": 8.5,
            "sdgs": ["Goal 2: Zero Hunger", "Goal 13: Climate Action"],
            "summary": "This research addresses critical food security issues..."
        }}
        """
        
        try:
            response = await self.client.generate_async(prompt, system_prompt="You are an impact analyst. Output JSON only.")
            
            # Robust JSON extraction
            try:
                # Try direct parse first in case it's clean
                return json.loads(response.strip())
            except json.JSONDecodeError:
                # Fallback to brace depth-tracking extraction
                start_idx = response.find("{")
                if start_idx != -1:
                    brace_count = 0
                    end_idx = -1
                    for i, char in enumerate(response[start_idx:]):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = start_idx + i
                                break
                    if end_idx != -1:
                        try:
                            return json.loads(response[start_idx:end_idx+1])
                        except json.JSONDecodeError:
                            print("Brace match found JSON object but could not be parsed.")
                
                print("Failed to find valid JSON in LLM response.")
                return {"score": 0, "sdgs": [], "summary": "Invalid JSON response from model.", "error": "parse_error"}
                
        except Exception as e:
            print(f"Impact analysis failed: {e}")
            return {"score": 0, "sdgs": [], "summary": "Could not analyze impact.", "error": str(e)}
