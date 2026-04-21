import sys
from pathlib import Path
# Add project root to sys.path so 'src' can be found
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config import LLMConfig
from src.crawlers.smart_crawler import SmartCrawler
from src.processors.pdf_distiller import DeepDistiller
from src.chatbot.ollama_client import get_ollama_client, DEFAULT_MODEL

def verify_models():
    print("--- Model Configuration Verification ---")
    print(f"Config CHAT_MODEL: {LLMConfig.CHAT_MODEL}")
    print(f"Config PIPELINE_MODEL: {LLMConfig.PIPELINE_MODEL}")
    print(f"OllamaClient DEFAULT_MODEL: {DEFAULT_MODEL}")
    
    # 1. Check Chat/Web App Client
    chat_client = get_ollama_client()
    print(f"Chat Client Model: {chat_client.model} [{'✅' if chat_client.model == LLMConfig.CHAT_MODEL else '❌'}]")
    
    # 2. Check Crawler (Pipeline)
    crawler = SmartCrawler()
    print(f"Crawler Client Model: {crawler.llm_client.model} [{'✅' if crawler.llm_client.model == LLMConfig.PIPELINE_MODEL else '❌'}]")
    
    # 3. Check Distiller (Pipeline)
    distiller = DeepDistiller()
    print(f"Distiller Client Model: {distiller.llm_client.model} [{'✅' if distiller.llm_client.model == LLMConfig.PIPELINE_MODEL else '❌'}]")

if __name__ == "__main__":
    verify_models()
