from dataclasses import dataclass, field
from typing import List, Optional
import uuid
from datetime import datetime

@dataclass
class Idea:
    """Represents a research idea or collaboration proposal."""
    title: str
    description: str
    author_name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    author_id: Optional[str] = None
    author_email: Optional[str] = None
    college: Optional[str] = None
    department: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    status: str = "Open"  # Open, In Progress, Completed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    collaborators: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "author_name": self.author_name,
            "author_id": self.author_id,
            "author_email": self.author_email,
            "college": self.college,
            "department": self.department,
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at,
            "collaborators": self.collaborators
        }

@dataclass
class Professor:
    """Represents a faculty member."""
    name: str
    url: str
    department: Optional[str] = None
    college: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    research_interests: List[str] = field(default_factory=list)
    research_areas: List[str] = field(default_factory=list)
@dataclass
class ResearchArea:
    """Represents a research area."""
    name: str
    url: str
    faculty: List[str] = field(default_factory=list)
    description: Optional[str] = None
    college: Optional[str] = None

@dataclass
class Publication:
    """Represents a research paper."""
    title: str
    author_id: str
    year: Optional[int] = None
    url: Optional[str] = None
    citations: int = 0
    pdf_url: Optional[str] = None

@dataclass
class Document:
    """Generic document for vector store."""
    id: str
    content: str
    metadata: dict = field(default_factory=dict)
