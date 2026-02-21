import os
import json
import time
import typing
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()

console = Console()

class GeminiClient:
    """Wrapper for Google Gemini API for structured data extraction."""
    
    def __init__(self, model_name: str = "gemini-flash-latest"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
            
        genai.configure(api_key=api_key)
        
        # Generation config for JSON mode
        self.generation_config = genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        self.request_count = 0
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Simple rate limiting (15 RPM = 1 request every 4 seconds for free tier)."""
        # Increase to 10s to be safe against burst limits
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < 10.0:
            time.sleep(10.0 - elapsed)
        self.last_request_time = time.time()

    def generate_json(self, prompt: str, schema: typing.Optional[dict] = None) -> typing.Any:
        """
        Generate structured JSON from a prompt with retry logic.
        """
        max_retries = 5
        base_delay = 10
        
        for attempt in range(max_retries):
            self._rate_limit()
            
            try:
                response = self.model.generate_content(prompt)
                self.request_count += 1
                
                # Extract JSON text
                text = response.text
                
                # Clean up markdown code blocks if present
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                    
                return json.loads(text)
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Quota exceeded" in error_str:
                    wait_time = base_delay * (2 ** attempt)
                    console.print(f"[yellow]Rate limit hit. Retrying in {wait_time}s...[/]")
                    time.sleep(wait_time)
                    continue
                else:
                    console.print(f"[red]Gemini API Error: {e}[/]")
                    return None
        
        console.print("[red]Max retries exceeded.[/]")
        return None

if __name__ == "__main__":
    # Test
    try:
        client = GeminiClient()
        print("Gemini Client Initialized.")
        res = client.generate_json('List 3 distinct colors in JSON format: {"colors": []}')
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Failed to init: {e}")
