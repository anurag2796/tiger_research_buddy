import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from pathlib import Path
import shutil
import json
from src.knowledge_graph.entity_resolver import EntityResolver

@pytest.fixture
def resolver(tmp_path):
    """Create an EntityResolver with a temporary data directory."""
    return EntityResolver(tmp_path)

def test_resolve_exact_match(resolver):
    """Test exact string matching."""
    id1 = resolver.resolve_faculty("Christopher Kanan", "Computer Science")
    id2 = resolver.resolve_faculty("Christopher Kanan", "Computer Science")
    assert id1 == id2
    assert id1.startswith("faculty_")

def test_resolve_fuzzy_match(resolver):
    """Test fuzzy matching for minor variations."""
    # First entry
    id1 = resolver.resolve_faculty("Christopher Kanan", "Computer Science")
    
    # Variation: Initial
    id2 = resolver.resolve_faculty("C. Kanan", "Computer Science")
    assert id1 == id2, "Should resolve 'C. Kanan' to 'Christopher Kanan'"
    
    # Variation: Missing Dept (should still match based on name confidence)
    id3 = resolver.resolve_faculty("Christopher Kanan")
    assert id1 == id3

def test_spelling_mistake(resolver):
    """Test Levenshtein distance correction."""
    id1 = resolver.resolve_faculty("Christopher Kanan")
    
    # Typo: "Chirstopher"
    id2 = resolver.resolve_faculty("Chirstopher Kanan")
    assert id1 == id2, "Should resolve typo 'Chirstopher' to 'Christopher'"

def test_phonetic_match(resolver):
    """Test phonetic matching."""
    id1 = resolver.resolve_faculty("Christopher Kanan")
    
    # Phonetic: "Kristopher Kanan"
    id2 = resolver.resolve_faculty("Kristopher Kanan")
    assert id1 == id2, "Should resolve 'Kristopher' to 'Christopher' via phonetics"

def test_blacklist(resolver):
    """Test blacklist rejection."""
    id1 = resolver.resolve_faculty("Unknown Author")
    assert id1 == "unknown_faculty"
    
    id2 = resolver.resolve_faculty("et al.")
    assert id2 == "unknown_faculty"

def test_publication_resolution(resolver):
    """Test publication deduplication."""
    t1 = "Attention Is All You Need"
    t2 = "attention is all you need"
    t3 = "Attention Is All You Need!"
    
    h1 = resolver.resolve_publication(t1, [])
    h2 = resolver.resolve_publication(t2, [])
    h3 = resolver.resolve_publication(t3, [])
    
    assert h1 == h2
    assert h1 == h3


# ---------------------------------------------------------------------------
# Graph-Context (Relational-Aware) Tests
# ---------------------------------------------------------------------------

def _build_shared_graph():
    """
    Two faculty nodes that share 3 co-authored papers and 2 concepts.
    Jaccard of shared neighbors = 5 / (2 + 5) ≈ 0.71  (well above 0.4).
    """
    G = nx.DiGraph()

    # Faculty nodes
    G.add_node("Christopher Kanan", type="faculty")
    G.add_node("C. Kanan", type="faculty")

    # Shared neighbors (papers + concepts)
    for paper in ["paper_aaa", "paper_bbb", "paper_ccc"]:
        G.add_node(paper, type="paper")
        G.add_edge("Christopher Kanan", paper)
        G.add_edge("C. Kanan", paper)

    for concept in ["deep_learning", "computer_vision"]:
        G.add_node(concept, type="concept")
        G.add_edge("Christopher Kanan", concept)
        G.add_edge("C. Kanan", concept)

    # Unique neighbors so the sets aren't identical
    G.add_node("paper_only_full", type="paper")
    G.add_edge("Christopher Kanan", "paper_only_full")
    G.add_node("paper_only_abbr", type="paper")
    G.add_edge("C. Kanan", "paper_only_abbr")

    return G


def _build_disjoint_graph():
    """
    Two name-forms that would fuzzy-match (~83%) but live in completely
    different neighborhoods.  Jaccard = 0 / (4+4) = 0.0.
    We use "C. Kanan" (an initial) so the first-name penalty does NOT fire,
    forcing the Jaccard check to be the deciding factor.
    """
    G = nx.DiGraph()

    G.add_node("Christopher Kanan", type="faculty")
    G.add_node("C. Kanan", type="faculty")

    # Christopher's world — vision/CS
    for n in ["paper_vision1", "paper_vision2", "deep_learning", "cv_concept"]:
        G.add_node(n)
        G.add_edge("Christopher Kanan", n)

    # C. Kanan's world — biology (completely disjoint)
    for n in ["paper_bio1", "paper_bio2", "genetics", "molecular_bio"]:
        G.add_node(n)
        G.add_edge("C. Kanan", n)

    return G


import networkx as nx


def test_graph_context_merge(tmp_path):
    """
    When fuzzy score is in the ambiguous zone (80-95%) AND the 1-hop
    neighbor overlap exceeds the Jaccard threshold, the resolver should
    merge the two names into one canonical entity.
    """
    G = _build_shared_graph()
    resolver = EntityResolver(tmp_path, graph=G, jaccard_threshold=0.4)

    id_full = resolver.resolve_faculty("Christopher Kanan", "Computer Science")
    id_abbr = resolver.resolve_faculty("C. Kanan", "Computer Science")

    assert id_full == id_abbr, (
        "Graph overlap (Jaccard ≈ 0.71) should confirm the merge "
        "for an ambiguous fuzzy match."
    )


def test_graph_context_keeps_distinct(tmp_path):
    """
    Even with an ~83% fuzzy match ('C. Kanan' vs 'Christopher Kanan'),
    the resolver must keep two entities separate when their graph
    neighborhoods have zero overlap (Jaccard = 0.0 < 0.4 threshold).
    """
    G = _build_disjoint_graph()
    resolver = EntityResolver(tmp_path, graph=G, jaccard_threshold=0.4)

    id_christopher = resolver.resolve_faculty("Christopher Kanan", "Computer Science")
    id_c_kanan = resolver.resolve_faculty("C. Kanan", "Biology")

    assert id_christopher != id_c_kanan, (
        "Zero graph overlap (Jaccard = 0.0) should block the merge "
        "despite an ~83% fuzzy string match."
    )
