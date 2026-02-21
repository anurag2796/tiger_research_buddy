import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.generation.synthesizer import ResponseSynthesizer

def test_synthesis():
    synthesizer = ResponseSynthesizer()
    
    # Mock results from HybridRetriever (List[Dict])
    mock_results = [
        {
            "id": "prof_kanan",
            "content": "Christopher Kanan is an Associate Professor in the Carlson Center for Imaging Science. He works on deep learning, computer vision, and brain-inspired AI.",
            "metadata": {
                "doc_type": "professor",
                "name": "Christopher Kanan",
                "title": "Associate Professor",
                "department": "CIS"
            },
            "rrf_score": 0.032
        },
        {
            "id": "paper_vqa",
            "content": "Visual Question Answering (VQA) is a task where a system answers questions about an image. Kanan et al. proposed a new baseline.",
            "metadata": {
                "doc_type": "research_paper",
                "title": "Making VQA Work",
                "source_node": "Christopher Kanan"
            },
            "rrf_score": 0.028
        }
    ]
    
    query = "Who works on computer vision?"
    print(f"Testing synthesis for query: '{query}'")
    
    try:
        response = synthesizer.synthesize(query, mock_results)
        print("\n--- Generated Response ---\n")
        print(response)
        print("\n--------------------------\n")
        print("✅ Synthesis Test Passed")
    except Exception as e:
        print(f"❌ Synthesis Test Failed: {e}")
        raise e

if __name__ == "__main__":
    test_synthesis()
