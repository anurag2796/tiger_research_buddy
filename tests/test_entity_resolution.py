
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
