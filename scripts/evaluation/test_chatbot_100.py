#!/usr/bin/env python3
"""
Comprehensive TigerResearchBuddy chatbot test with 100 prompts

Prompt Categories:
- 40 Contextual (RIT research-related)
- 30 Off-topic (general knowledge)
- 15 Small talk (greetings, thank you, etc.)
- 15 Meaningless/Gibberish

Results are stored in test_results_100_<timestamp>.md
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

# ==================== TEST PROMPTS ====================

# Category 1: Contextual/In-Domain (40 prompts)
CONTEXTUAL_PROMPTS = [
    # General research area queries
    "Who works on machine learning?",
    "Tell me about AI research",
    "Which professors do cybersecurity research?",
    "Who can I work with for computer vision?",
    "Are there any NLP researchers?",
    "Who works on software engineering?",
    "Tell me about data science faculty",
    "Who researches robotics?",
    "Which professors work on networking?",
    "Who does database research?",
    
    # Specific professor queries
    "Tell me about Professor Merkel",
    "What does Christopher Kanan research?",
    "Who is Zack Butler?",
    "Tell me about Dr. Bailey",
    "What papers has Cory Merkel published?",
    
    # Project/opportunity queries
    "I want to do undergraduate research. Who should I contact?",
    "Are there any PhD positions available?",
    "How do I get involved in research?",
    "Which professors take undergraduate students?",
    "I'm looking for a research advisor",
    
    # Specific technical areas
    "Who works on deep learning?",
    "Tell me about HCI research",
    "Which professors do blockchain research?",
    "Who researches quantum computing?",
    "Are there any faculty working on IoT?",
    "Who does cloud computing research?",
    "Tell me about security research",
    "Which professors work on compilers?",
    "Who researches operating systems?",
    "Are there any game development professors?",
    
    # Department/program queries  
    "What research areas are available?",
    "Tell me about the CS department",
    "What's the difference between CS and SE?",
    "Are there any interdisciplinary research opportunities?",
    
    # Comparison queries
    "Who are the top AI researchers?",
    "Which professor has the most publications?",
    "Who should I contact for ML vs NLP?",
    
    # Follow-up style queries
    "What about computer graphics?",
    "Anyone else?",
    "What's their email?",
    "Where's their office?",
]

# Category 2: Off-Topic/Out-of-Domain (30 prompts)
OFF_TOPIC_PROMPTS = [
    # General knowledge
    "What's the weather like today?",
    "Who won the Super Bowl?",
    "What is the capital of France?",
    "How tall is Mount Everest?",
    "When was World War 2?",
    "What's the population of China?",
    "Who invented the telephone?",
    "What's the speed of light?",
    
    # How-to questions
    "How do I make a chocolate cake?",
    "How do I tie a tie?",
    "How do I change a tire?",
    "How do I learn Spanish?",
    "How do I invest in stocks?",
    
    # Local/personal questions
    "What's the best pizza place in Rochester?",
    "Where can I buy groceries?",
    "What movies are playing this weekend?",
    "When does the library close?",
    "How do I get to campus?",
    
    # Current events
    "What's happening in the news?",
    "Who is the president?",
    "What's the stock market doing?",
    
    # Random factual
    "How much does a Tesla cost?",
    "What's the meaning of life?",
    "Why is the sky blue?",
    "How do airplanes fly?",
    "What causes earthquakes?",
    "How does photosynthesis work?",
    "What is quantum mechanics?",
    "How do computers work?",
]

# Category 3: Small Talk (15 prompts)
SMALL_TALK_PROMPTS = [
    # Greetings
    "Hello",
    "Hi there",
    "Good morning",
    "Hey",
    
    # Gratitude
    "Thank you",
    "Thanks!",
    "That was helpful",
    
    # Feedback
    "You're awesome",
    "Great job",
    "I appreciate it",
    
    # General chat
    "How are you?",
    "What's up?",
    "Can you help me?",
    "I have a question",
    "I need assistance",
]

# Category 4: Meaningless/Gibberish (15 prompts)
MEANINGLESS_PROMPTS = [
    # Typos/incomplete
    "asdf",
    "jkl;",
    "qwerty",
    "zzz",
    "mmmm",
    
    # Nonsense
    "buffalo buffalo buffalo",
    "colorless green ideas sleep furiously",
    "the quick brown fox jumps over the lazy dog but why though",
    
    # Random characters
    "!!!???",
    "......",
    "123456789",
    
    # Mixed gibberish
    "research ML AI cyber quantum blockchain",
    "professor professor professor",
    "who what where when why how",
    "error error error help",
]


def format_test_result(prompt: str, response: str, duration: float, category: str, number: int) -> str:
    """Format a single test result as markdown"""
    return f"""
### Test {number}: "{prompt}"
**Category**: {category}  
**Response Time**: {duration:.2f}s

**Response**:
```
{response[:500]}{'...' if len(response) > 500 else ''}
```

---
"""


def run_comprehensive_test():
    """Run all 100 test prompts and save results"""
    print("🐅 TigerResearchBuddy Comprehensive Test Suite (100 Prompts)")
    print("=" * 70)
    print("Initializing RAG engine with Ollama (local LLM)...")
    
    # Initialize engine with Ollama
    vector_store = get_vector_store()
    vector_store.initialize()
    
    ollama_client = get_ollama_client()
    ollama_client.initialize()
    
    engine = RAGEngine(vector_store=vector_store, gemini_client=ollama_client)
    engine.initialize()
    
    print("\n✓ Engine ready!")
    print("\nTest Breakdown:")
    print(f"  - Contextual (RIT research): {len(CONTEXTUAL_PROMPTS)} prompts")
    print(f"  - Off-topic: {len(OFF_TOPIC_PROMPTS)} prompts")
    print(f"  - Small talk: {len(SMALL_TALK_PROMPTS)} prompts")
    print(f"  - Meaningless/Gibberish: {len(MEANINGLESS_PROMPTS)} prompts")
    print(f"  TOTAL: {len(CONTEXTUAL_PROMPTS) + len(OFF_TOPIC_PROMPTS) + len(SMALL_TALK_PROMPTS) + len(MEANINGLESS_PROMPTS)} prompts")
    print("=" * 70)
    
    # Prepare results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_100_{timestamp}.md"
    
    all_results = []
    all_results.append(f"# TigerResearchBuddy Comprehensive Test Results (100 Prompts)\n")
    all_results.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # Track statistics by category
    stats = {
        "Contextual": {"times": [], "errors": 0},
        "Off-Topic": {"times": [], "errors": 0},
        "Small Talk": {"times": [], "errors": 0},
        "Meaningless": {"times": [], "errors": 0}
    }
    
    total_prompts = 0
    
    # Test Category 1: Contextual
    all_results.append("## Category 1: Contextual (RIT Research) Prompts\n")
    all_results.append(f"Testing {len(CONTEXTUAL_PROMPTS)} research-related queries.\n\n")
    
    for i, prompt in enumerate(CONTEXTUAL_PROMPTS, 1):
        total_prompts += 1
        print(f"\n[{total_prompts}/100] Contextual: {prompt[:60]}...")
        
        start = time.time()
        try:
            response = engine.query(prompt, n_results=4)
            duration = time.time() - start
            stats["Contextual"]["times"].append(duration)
            
            all_results.append(format_test_result(prompt, response, duration, "Contextual", total_prompts))
            print(f"  ✓ {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start
            stats["Contextual"]["errors"] += 1
            all_results.append(format_test_result(prompt, f"ERROR: {str(e)}", duration, "Contextual (ERROR)", total_prompts))
            print(f"  ✗ Error: {e}")
    
    # Clear history between categories
    engine.clear_history()
    
    # Test Category 2: Off-Topic
    all_results.append("\n## Category 2: Off-Topic Prompts\n")
    all_results.append(f"Testing {len(OFF_TOPIC_PROMPTS)} general knowledge queries.\n\n")
    
    for i, prompt in enumerate(OFF_TOPIC_PROMPTS, 1):
        total_prompts += 1
        print(f"\n[{total_prompts}/100] Off-Topic: {prompt[:60]}...")
        
        start = time.time()
        try:
            response = engine.query(prompt, n_results=4)
            duration = time.time() - start
            stats["Off-Topic"]["times"].append(duration)
            
            all_results.append(format_test_result(prompt, response, duration, "Off-Topic", total_prompts))
            print(f"  ✓ {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start
            stats["Off-Topic"]["errors"] += 1
            all_results.append(format_test_result(prompt, f"ERROR: {str(e)}", duration, "Off-Topic (ERROR)", total_prompts))
            print(f"  ✗ Error: {e}")
    
    engine.clear_history()
    
    # Test Category 3: Small Talk
    all_results.append("\n## Category 3: Small Talk Prompts\n")
    all_results.append(f"Testing {len(SMALL_TALK_PROMPTS)} conversational queries.\n\n")
    
    for i, prompt in enumerate(SMALL_TALK_PROMPTS, 1):
        total_prompts += 1
        print(f"\n[{total_prompts}/100] Small Talk: {prompt[:60]}...")
        
        start = time.time()
        try:
            response = engine.query(prompt, n_results=4)
            duration = time.time() - start
            stats["Small Talk"]["times"].append(duration)
            
            all_results.append(format_test_result(prompt, response, duration, "Small Talk", total_prompts))
            print(f"  ✓ {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start
            stats["Small Talk"]["errors"] += 1
            all_results.append(format_test_result(prompt, f"ERROR: {str(e)}", duration, "Small Talk (ERROR)", total_prompts))
            print(f"  ✗ Error: {e}")
    
    engine.clear_history()
    
    # Test Category 4: Meaningless
    all_results.append("\n## Category 4: Meaningless/Gibberish Prompts\n")
    all_results.append(f"Testing {len(MEANINGLESS_PROMPTS)} nonsensical queries.\n\n")
    
    for i, prompt in enumerate(MEANINGLESS_PROMPTS, 1):
        total_prompts += 1
        print(f"\n[{total_prompts}/100] Meaningless: {prompt[:60]}...")
        
        start = time.time()
        try:
            response = engine.query(prompt, n_results=4)
            duration = time.time() - start
            stats["Meaningless"]["times"].append(duration)
            
            all_results.append(format_test_result(prompt, response, duration, "Meaningless", total_prompts))
            print(f"  ✓ {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start
            stats["Meaningless"]["errors"] += 1
            all_results.append(format_test_result(prompt, f"ERROR: {str(e)}", duration, "Meaningless (ERROR)", total_prompts))
            print(f"  ✗ Error: {e}")
    
    # Generate statistics
    all_results.append("\n## Test Statistics\n\n")
    
    total_time = 0
    total_successful = 0
    
    for category, data in stats.items():
        if data["times"]:
            avg_time = sum(data["times"]) / len(data["times"])
            min_time = min(data["times"])
            max_time = max(data["times"])
            successful = len(data["times"])
            total_successful += successful
            total_time += sum(data["times"])
            
            all_results.append(f"### {category}\n")
            all_results.append(f"- Prompts: {successful + data['errors']}\n")
            all_results.append(f"- Successful: {successful}\n")
            all_results.append(f"- Errors: {data['errors']}\n")
            all_results.append(f"- Avg response time: {avg_time:.2f}s\n")
            all_results.append(f"- Min: {min_time:.2f}s, Max: {max_time:.2f}s\n\n")
    
    # Overall statistics
    all_results.append("### Overall\n")
    all_results.append(f"- Total prompts: {total_prompts}\n")
    all_results.append(f"- Successful: {total_successful}\n")
    all_results.append(f"- Total errors: {sum(d['errors'] for d in stats.values())}\n")
    all_results.append(f"- Success rate: {(total_successful/total_prompts)*100:.1f}%\n")
    all_results.append(f"- Total test time: {total_time:.1f}s ({total_time/60:.1f} minutes)\n")
    all_results.append(f"- Average per prompt: {total_time/total_prompts:.2f}s\n\n")
    
    # Quality assessment
    all_results.append("\n## Quality Assessment Checklist\n\n")
    all_results.append("**Manual Review Items**:\n\n")
    all_results.append("**Contextual Prompts**:\n")
    all_results.append("- [ ] Do responses cite real RIT faculty names?\n")
    all_results.append("- [ ] Is contact information (email, office) included?\n")
    all_results.append("- [ ] Are responses formatted per `skills.md`?\n")
    all_results.append("- [ ] No hallucinated professor names or papers?\n\n")
    
    all_results.append("**Off-Topic Prompts**:\n")
    all_results.append("- [ ] Does bot admit lack of RIT-specific knowledge?\n")
    all_results.append("- [ ] Are responses appropriately brief?\n")
    all_results.append("- [ ] No attempts to answer non-RIT questions?\n\n")
    
    all_results.append("**Small Talk Prompts**:\n")
    all_results.append("- [ ] Friendly and professional tone?\n")
    all_results.append("- [ ] Appropriate responses to greetings?\n")
    all_results.append("- [ ] Guides user back to research queries?\n\n")
    
    all_results.append("**Meaningless Prompts**:\n")
    all_results.append("- [ ] Handles gibberish gracefully?\n")
    all_results.append("- [ ] Doesn't attempt to force meaning?\n")
    all_results.append("- [ ] Politely asks for clarification?\n\n")
    
    # Write to file
    with open(results_file, 'w') as f:
        f.write(''.join(all_results))
    
    print("\n" + "=" * 70)
    print(f"✓ Testing complete!")
    print(f"✓ Results saved to: {results_file}")
    print(f"\nSummary:")
    print(f"  Total: {total_prompts} prompts")
    print(f"  Successful: {total_successful} ({(total_successful/total_prompts)*100:.1f}%)")
    print(f"  Errors: {sum(d['errors'] for d in stats.values())}")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"  Avg per prompt: {total_time/total_prompts:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    run_comprehensive_test()
