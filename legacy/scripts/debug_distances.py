
import sys
import os
sys.path.append(os.getcwd())

from src.database.vector_store import get_vector_store

def check_distances():
    vs = get_vector_store()
    vs.initialize()
    
    queries = [
        "Christopher Kanan",  # Known faculty
        "Machine Learning",   # Known topic
        "Professor FakeName", # Hallucination check
        "agsdg sdgsdg",       # Gibberish
        "How to bake a cake"  # Off-topic
    ]
    
    print("\n=== Distance Analysis ===")
    for q in queries:
        results = vs.search(q, n_results=3)
        print(f"\nQuery: '{q}'")
        for i, res in enumerate(results):
            dist = res.get('distance', 'N/A')
            content = res.get('content', '')[:50]
            print(f"  {i+1}. Dist: {dist} | Content: {content}...")

if __name__ == "__main__":
    check_distances()
