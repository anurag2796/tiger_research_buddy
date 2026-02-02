"""Data models for TigerResearchBuddy."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Publication:
    """Represents an academic publication."""
    title: str
    year: str = ""
    citations: int = 0
    venue: str = ""
    authors: list[str] = field(default_factory=list)


@dataclass
class Professor:
    """Represents a faculty member."""
    name: str
    title: str = ""
    department: str = ""
    profile_url: str = ""
    email: str = ""
    research_interests: list[str] = field(default_factory=list)
    publications: list[Publication] = field(default_factory=list)
    citations: int = 0
    h_index: int = 0
    
    def to_text(self) -> str:
        """Convert to searchable text."""
        parts = [
            f"Professor: {self.name}",
            f"Title: {self.title}" if self.title else "",
            f"Department: {self.department}" if self.department else "",
            f"Research interests: {', '.join(self.research_interests)}" if self.research_interests else "",
        ]
        return "\n".join(p for p in parts if p)


@dataclass
class ResearchArea:
    """Represents a research area at RIT."""
    name: str
    url: str = ""
    description: str = ""
    faculty: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    
    def to_text(self) -> str:
        """Convert to searchable text."""
        parts = [
            f"Research Area: {self.name}",
            f"Description: {self.description}" if self.description else "",
            f"Keywords: {', '.join(self.keywords)}" if self.keywords else "",
            f"Faculty: {', '.join(self.faculty)}" if self.faculty else "",
        ]
        return "\n".join(p for p in parts if p)


@dataclass
class Document:
    """A document for the vector store."""
    id: str
    content: str
    doc_type: str  # "research_area", "professor", "publication"
    metadata: dict = field(default_factory=dict)
