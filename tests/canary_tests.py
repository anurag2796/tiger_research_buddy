#!/usr/bin/env python3
"""
Canary Tests for TigerResearchBuddy

Quick smoke tests that should always pass.
Run daily to catch regressions.

Tests 5 critical scenarios:
1. Faculty lookup
2. Topic search
3. Follow-up (context awareness)
4.Off-topic (should refuse)
5. Hallucination prevention (non-existent faculty)
"""

import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.chatbot.rag_engine import RAGEngine
from src.database.vector_store import get_vector_store
from src.chatbot.ollama_client import get_ollama_client

# Canary queries - these MUST always work
CANARY_TESTS = [
    {
        "id": 1,
        "query": "Who is Christopher Kanan?",
        "type": "faculty_lookup",
        "must_contain": ["Christopher Kanan", "kanan"],
        "must_not_contain": ["Result 1:", "Context:", "✅ GOOD"],
        "max_time": 10.0,
    },
    {
        "id": 2,
        "query": "Who works on machine learning?",
        "type": "topic_search",
        "must_contain": ["machine learning"], # Removed "ML" - synonymous but not guaranteed
        "must_not_contain": ["Result 1:", "professor:", "research_area:"],
        "max_time": 10.0,
    },
    {
        "id": 3,
        "query": "What's his email?",
        "type": "follow_up",
        "context_query": "Who is Christopher Kanan?",
        "must_contain": ["@rit.edu"],
        "must_not_contain": ["Result 1", "Result 2", "Context:"],
        "max_time": 10.0,
    },
    {
        "id": 4,
        "query": "What's the weather like today?",
        "type": "off_topic",
        "must_contain": ["specialize", "RIT Computing"],
        "must_not_contain": ["weather", "temperature", "forecast"],
        "max_time": 5.0,
    },
    {
        "id": 5,
        "query": "Who is Professor FakeName?",
        "type": "hallucination_check",
        "must_contain": ["don't have", "not found", "cannot find"],
        "must_not_contain": ["FakeName works", "FakeName is", "FakeName researches"],
        "max_time": 10.0,
    },
]


class CanaryTestResult:
    """Result of a single canary test"""
    def __init__(self, test_id, query, passed, duration, issues):
        self.test_id = test_id
        self.query = query
        self.passed = passed
        self.duration = duration
        self.issues = issues


def run_canary_tests():
    """Run all canary tests and return results"""
    print("🐅 TigerResearchBuddy Canary Tests")
    print("=" * 60)
    print("Initializing...")
    
    # Initialize engine (use Ollama for free testing)
    vector_store = get_vector_store()
    vector_store.initialize()
    
    ollama_client = get_ollama_client()
    ollama_client.initialize()
    
    engine = RAGEngine(vector_store=vector_store, gemini_client=ollama_client)
    engine.initialize()
    
    print("✓ Engine ready\n")
    
    results = []
    passed_count = 0
    
    for test in CANARY_TESTS:
        test_id = test["id"]
        query = test["query"]
        test_type = test["type"]
        
        print(f"[Test {test_id}] {test_type}: \"{query[:50]}...\"")
        
        issues = []
        
        # Set up context if needed (for follow-up tests)
        if test.get("context_query"):
            engine.query(test["context_query"])
        
        # Run query
        start = time.time()
        try:
            response = engine.query(query, n_results=4)
            duration = time.time() - start
        except Exception as e:
            duration = time.time() - start
            issues.append(f"ERROR: {str(e)}")
            results.append(CanaryTestResult(test_id, query, False, duration, issues))
            print(f"  ✗ FAILED: {e}")
            continue
        
        # Check response time
        if duration > test["max_time"]:
            issues.append(f"Too slow: {duration:.2f}s > {test['max_time']}s")
        
        # Check required content (require ALL)
        response_lower = response.lower()
        for required in test.get("must_contain", []):
            if required.lower() not in response_lower:
                issues.append(f"Missing required: '{required}'")
        
        # Check forbidden content
        for forbidden in test.get("must_not_contain", []):
            if forbidden.lower() in response_lower:
                issues.append(f"Contains forbidden artifact: '{forbidden}'")
        
        # Special check for hallucination test (require ANY)
        if test_type == "hallucination_check":
             # We want at least one of the negative phrases
             negatives = test.get("must_contain", [])
             if not any(neg.lower() in response_lower for neg in negatives):
                 issues.append(f"Response didn't refuse properly (expected one of: {negatives})")
             # Clear issues added by the loop above since we handled it here
             # This is a bit hacky but keeps the structure simple
             issues = [i for i in issues if not i.startswith("Missing required:")]
             if not any(neg.lower() in response_lower for neg in negatives):
                 issues.append(f"Missing refusal phrase")

        # Determine pass/fail
        passed = len(issues) == 0
        if passed:
            passed_count += 1
        
        results.append(CanaryTestResult(test_id, query, passed, duration, issues))
        
        # Print result
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status} ({duration:.2f}s)")
        if issues:
            for issue in issues:
                print(f"    - {issue}")
            print(f"    [DEBUG] Response start: {response[:100].replace(chr(10), ' ')}...")
        
        # Clear history between independent tests
        if test_id != 3:  # Don't clear for follow-up test
            engine.clear_history()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed_count}/{len(CANARY_TESTS)} passed")
    
    if passed_count == len(CANARY_TESTS):
        print("✅ ALL CANARY TESTS PASSED")
        return 0
    else:
        print(f"❌ {len(CANARY_TESTS) - passed_count} CANARY TESTS FAILED")
        print("\nFailed tests:")
        for result in results:
            if not result.passed:
                print(f"  - Test {result.test_id}: {result.query[:50]}")
                for issue in result.issues:
                    print(f"      {issue}")
        return 1


if __name__ == "__main__":
    exit_code = run_canary_tests()
    sys.exit(exit_code)
