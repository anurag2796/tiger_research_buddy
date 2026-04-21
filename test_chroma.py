import json
from pathlib import Path
import chromadb

# Setup paths similar to the app
PROJECT_ROOT = Path("/home/lab/codebase/projects/personalProjects/tiger_research_buddy")
CHROMA_DIR = PROJECT_ROOT / "data/restricted/chroma"

print(f"Checking Chroma directory: {CHROMA_DIR}")
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
try:
    collections = client.list_collections()
    print(f"Available collections: {[c.name for c	in collections]}")

    # We know the collection name from config
    collection_name = "rit_research_restricted"
    collection = client.get_or_create_collection(name=collection_name)
    print(f"Collection '{collection_name}' ready.")

    # Add a dummy document to ensure we have something to query
    collection.add(
        documents=["This is a test document about Christopher Kanan."],
        metadatas=[{"doc_type": "professor", "name": "Christopher Kanan"}],
        ids=["test_doc_1"]
    )
    print("Added dummy document.")

    print(f"Document count: {collection.count()}")

    # Try a query
    query = "Who is Christopher Kanan?"
    print(f"Querying: '{query}'")
    results = collection.query(query_texts=[query], n_results=1)

    if results["documents"] and len(results["documents"][0]) > 0:
        print("Results found!")
        for i, doc in enumerate(results["documents"][0]):
            print(f"  Result {i}: {doc[:100]}...")
            print(f"  Metadata: {results['metadatas'][0][i]}")
    else:
        print("No results found for the query.")

except Exception as e:
    print(f"Error: {e}")
    exit(1)
