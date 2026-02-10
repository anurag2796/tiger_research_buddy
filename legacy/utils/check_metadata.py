
import sys
import os
sys.path.append(os.getcwd())

from src.database.vector_store import get_vector_store

def check_metadata():
    vs = get_vector_store()
    vs.initialize()
    
    results = vs.search("Christopher Kanan", n_results=3)
    print("\n=== Metadata Check ===")
    for res in results:
        print(f"Content: {res['content'][:50]}...")
        print(f"Metadata: {res['metadata']}")

if __name__ == "__main__":
    check_metadata()
