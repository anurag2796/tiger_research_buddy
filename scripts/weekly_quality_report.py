#!/usr/bin/env python3
"""
Weekly Quality Report Generator

Runs comprehensive test suite and generates quality metrics report.
Tracks improvement over time.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.chatbot.rag_engine import RAGEngine
from src.database.vector_store import get_vector_store
from src.chatbot.ollama_client import get_ollama_client
from tests.evaluators.automated_evaluator import ResponseEvaluator

# Quick test suite (subset of 100)
QUICK_TEST_QUERIES = [
    # Faculty lookups
    "Who is Christopher Kanan?",
    "Tell me about Dr. Butler",
    "Who is Professor Merkel?",
    
    # Topic searches
    "Who works on machine learning?",
    "Which professors do AI research?",
    "Who researches cybersecurity?",
    
    # Contact info
    "What's Christopher Kanan's email?",
    "Where is Dr. Butler's office?",
    
    # Off-topic (should refuse)
    "What's the weather?",
    "How do I make a cake?",
    
    # Edge cases
    "Who is Professor FakeName?",
    "asdf qwerty",
]


def load_faculty_names():
    """Load known faculty names from database"""
    # Simple version - just return a few known names
    # In production, this would query the database
    return [
        "Christopher Kanan",
        "Zack Butler",
        "Cory Merkel",
        "Reynold Bailey",
        "Rajendra Raj",
    ]


def run_weekly_report():
    """Run weekly quality assessment"""
    print("🐅 TigerResearchBuddy Weekly Quality Report")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize
    print("Initializing system...")
    vector_store = get_vector_store()
    vector_store.initialize()
    
    ollama_client = get_ollama_client()
    ollama_client.initialize()
    
    engine = RAGEngine(vector_store=vector_store, gemini_client=ollama_client)
    engine.initialize()
    
    evaluator = ResponseEvaluator(known_faculty=load_faculty_names())
    
    print(f"Running {len(QUICK_TEST_QUERIES)} test queries...\n")
    
    results = []
    
    for i, query in enumerate(QUICK_TEST_QUERIES, 1):
        print(f"[{i}/{len(QUICK_TEST_QUERIES)}] {query[:60]}...", end=' ')
        
        start = time.time()
        try:
            response = engine.query(query, n_results=4)
            duration = time.time() - start
            
            # Evaluate response
            result = evaluator.evaluate_response(
                query=query,
                response=response,
                response_time=duration
            )
            results.append(result)
            
            status = "✓" if result.total_score >= 70 else "✗"
            print(f"{status} ({result.total_score}/100)")
            
        except Exception as e:
            print(f"✗ ERROR: {e}")
    
    print("\n" + "=" * 70)
    
    # Generate report
    report = evaluator.generate_report(results)
    print(report)
    
    # Save results
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"quality_report_{timestamp}.txt"
    
    with open(results_file, 'w') as f:
        f.write(f"TigerResearchBuddy Weekly Quality Report\n")
        f.write(f"Generated: {datetime.now()}\n\n")
        f.write(report)
    
    print(f"\n✓ Report saved to: {results_file}")
    
    # Calculate metrics
    avg_score = sum(r.total_score for r in results) / len(results)
    critical_failures = sum(1 for r in results if r.critical_failures)
    
    # Return exit code based on quality threshold
    if avg_score >= 70 and critical_failures == 0:
        print("\n✅ Quality meets standards")
        return 0
    else:
        print(f"\n⚠️  Quality below standards (avg: {avg_score:.1f}/100, critical: {critical_failures})")
        return 1


if __name__ == "__main__":
    exit_code = run_weekly_report()
    sys.exit(exit_code)
