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
            # Start/End json cleanup
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "{" not in json_str:
                return {"score": 0, "sdgs": [], "summary": "Analysis failed."}
                
            return json.loads(json_str)
        except Exception as e:
            print(f"Impact analysis failed: {e}")
            return {"score": 0, "sdgs": [], "summary": "Could not analyze impact."}
