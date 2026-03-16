import pytest
from src.utils.dedup import normalize_name, deduplicate_faculty

def test_normalize_name():
    assert normalize_name("John Doe") == "john doe"
    assert normalize_name("John D. Doe") == "john d doe"
    assert normalize_name("  Jane    Smith  ") == "jane smith"
    assert normalize_name(None) == ""
    assert normalize_name("") == ""
    assert normalize_name("José García-López") == "josé garcíalópez"

def test_deduplicate_faculty():
    faculty = [
        {
            "name": "Alan Turing",
            "bio": "Short bio.",
            "research_interests": ["Cryptanalysis"]
        },
        {
            "name": "Alan M. Turing", # Normalization might not catch the M. if it's there
            "bio": "A much longer and more detailed biography of Alan Turing.",
            "research_interests": ["Mathematics", "Computer Science"],
            "title": "Professor"
        },
        {
             "name": "alan turing ",
             "research_areas": ["AI"]
        },
        {
             "name": "Grace Hopper",
             "bio": "Pioneer",
             "research_interests": ["Compilers"]
        }
    ]
    
    # We expect 'Alan Turing' and 'alan turing ' to merge. 'Alan M. Turing' is treated as distinct by our simple logic, but let's test the Exact/Normalized match.
    deduped = deduplicate_faculty(faculty)
    
    # "Alan Turing" and "alan turing " merge -> 1
    # "Alan M. Turing" -> 1
    # "Grace Hopper" -> 1
    assert len(deduped) == 3
    
    # Let's find the merged Alan Turing
    merged_alan = next(f for f in deduped if f["name"] == "Alan Turing")
    assert merged_alan["bio"] == "Short bio." # Only one bio in the merged set for "Alan Turing"
    assert set(merged_alan["research_interests"]) == {"Cryptanalysis"}
    assert set(merged_alan["research_areas"]) == {"AI"}
    
def test_deduplicate_faculty_merged_fields():
    # Test strict duplicates
    faculty = [
        {
            "name": "Test Prof",
            "bio": "Short",
            "research_interests": ["A", "B"]
        },
        {
            "name": "Test Prof",
            "bio": "Longer bio here.",
            "research_interests": ["B", "C"],
            "title": "Dr."
        }
    ]
    
    deduped = deduplicate_faculty(faculty)
    assert len(deduped) == 1
    merged = deduped[0]
    
    assert merged["name"] == "Test Prof"
    assert merged["bio"] == "Longer bio here."
    assert set(merged["research_interests"]) == {"A", "B", "C"}
    assert merged["title"] == "Dr."

def test_deduplicate_faculty_empty():
    assert deduplicate_faculty([]) == []
    assert deduplicate_faculty([{}]) == []
    assert deduplicate_faculty([{"name": ""}]) == []
