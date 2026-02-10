#!/usr/bin/env python3
"""
Test TigerResearchBuddy chatbot with 20 prompts
- 10 contextual (RIT research-related) prompts
- 10 random off-topic prompts

Results are stored in test_results_<timestamp>.md
"""

import sys
import os
from datetime import datetime
from pathlib import Path
import time

# Add src to path
sys.path.append(os.getcwd())

from src.chatbot.rag_engine import RAGEngine
from src.database.vector_store import get_vector_store
from src.chatbot.ollama_client import get_ollama_client

# Test prompts
CONTEXTUAL_PROMPTS = [
    "Who works on machine learning at RIT?",
    "Tell me about AI research in the computing department",
    "I'm interested in cybersecurity. Which professors should I contact?",
    "Who can I work with for computer vision research?",
    "Are there any faculty researching natural language processing?",
    "Which professors work on software engineering?",
    "I want to do research in data science. Who should I talk to?",
    "Who works on robotics or autonomous systems?",
    "Tell me about professors doing research in networking",
    "Who researches databases or big data?"
]

RANDOM_PROMPTS = [
    "What's the weather like today?",
    "How do I make a chocolate cake?",
    "Who won the Super Bowl last year?",
    "What is the capital of France?",
    "Tell me a joke about programming",
    "What's the best pizza place in Rochester?",
    "How do I tie a tie?",
    "What movies are playing this weekend?",
    "What's the meaning of life?",
    "How much does a Tesla cost?"
]


def format_test_result(prompt: str, response: str, duration: float, test_type: str) -> str:
    """Format a single test result as markdown"""
    return f"""
### Prompt: "{prompt}"
**Type**: {test_type}  
**Response Time**: {duration:.2f}s

**Response**:
```
{response}
```

---
"""


def run_tests():
    """Run all test prompts and save results"""
    print("🐅 TigerResearchBuddy Test Suite")
    print("=" * 60)
    print("Initializing RAG engine with Ollama (local LLM)...")
    
    # Initialize engine with Ollama
    vector_store = get_vector_store()
    vector_store.initialize()
    
    ollama_client = get_ollama_client()
    ollama_client.initialize()
    
    engine = RAGEngine(vector_store=vector_store, gemini_client=ollama_client)
    engine.initialize()
    
    print("\n✓ Engine ready!")
    print(f"\nRunning {len(CONTEXTUAL_PROMPTS)} contextual + {len(RANDOM_PROMPTS)} random prompts...")
    print("=" * 60)
    
    # Prepare results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_{timestamp}.md"
    
    all_results = []
    all_results.append(f"# TigerResearchBuddy Test Results\n")
    all_results.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    all_results.append(f"**Total Prompts**: {len(CONTEXTUAL_PROMPTS) + len(RANDOM_PROMPTS)}\n\n")
    
    # Test contextual prompts
    all_results.append("## Part 1: Contextual Prompts (RIT Research)\n")
    all_results.append("These prompts are relevant to RIT faculty and research.\n\n")
    
    contextual_times = []
    for i, prompt in enumerate(CONTEXTUAL_PROMPTS, 1):
        print(f"\n[{i}/10] Contextual: {prompt[:50]}...")
        
        start = time.time()
        try:
            response = engine.query(prompt, n_results=4)
            duration = time.time() - start
            contextual_times.append(duration)
            
            all_results.append(format_test_result(prompt, response, duration, "Contextual"))
            print(f"  ✓ Response received ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start
            all_results.append(format_test_result(prompt, f"ERROR: {str(e)}", duration, "Contextual (ERROR)"))
            print(f"  ✗ Error: {e}")
    
    # Test random prompts
    all_results.append("\n## Part 2: Random Off-Topic Prompts\n")
    all_results.append("These prompts are unrelated to RIT research to test hallucination prevention.\n\n")
    
    random_times = []
    # Clear history to avoid context bleeding
    engine.clear_history()
    
    for i, prompt in enumerate(RANDOM_PROMPTS, 1):
        print(f"\n[{i}/10] Random: {prompt[:50]}...")
        
        start = time.time()
        try:
            response = engine.query(prompt, n_results=4)
            duration = time.time() - start
            random_times.append(duration)
            
            all_results.append(format_test_result(prompt, response, duration, "Random/Off-Topic"))
            print(f"  ✓ Response received ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start
            all_results.append(format_test_result(prompt, f"ERROR: {str(e)}", duration, "Random (ERROR)"))
            print(f"  ✗ Error: {e}")
    
    # Add statistics
    all_results.append("\n## Test Statistics\n\n")
    
    if contextual_times:
        avg_contextual = sum(contextual_times) / len(contextual_times)
        all_results.append(f"**Contextual Prompts**:\n")
        all_results.append(f"- Average response time: {avg_contextual:.2f}s\n")
        all_results.append(f"- Min: {min(contextual_times):.2f}s\n")
        all_results.append(f"- Max: {max(contextual_times):.2f}s\n\n")
    
    if random_times:
        avg_random = sum(random_times) / len(random_times)
        all_results.append(f"**Random Prompts**:\n")
        all_results.append(f"- Average response time: {avg_random:.2f}s\n")
        all_results.append(f"- Min: {min(random_times):.2f}s\n")
        all_results.append(f"- Max: {max(random_times):.2f}s\n\n")
    
    # Quality assessment
    all_results.append("\n## Quality Assessment Notes\n\n")
    all_results.append("**Things to check manually**:\n")
    all_results.append("1. Do contextual responses cite actual RIT faculty from the database?\n")
    all_results.append("2. Do random prompts properly admit lack of knowledge?\n")
    all_results.append("3. Are responses formatted according to `skills.md` guidelines?\n")
    all_results.append("4. Is contact information (email, office) included when relevant?\n")
    all_results.append("5. Are there any hallucinated professor names or papers?\n\n")
    
    # Write to file
    with open(results_file, 'w') as f:
        f.write(''.join(all_results))
    
    print("\n" + "=" * 60)
    print(f"✓ Testing complete!")
    print(f"✓ Results saved to: {results_file}")
    print(f"\nSummary:")
    if contextual_times:
        print(f"  Contextual: {len(contextual_times)} prompts, avg {avg_contextual:.2f}s")
    if random_times:
        print(f"  Random: {len(random_times)} prompts, avg {avg_random:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
