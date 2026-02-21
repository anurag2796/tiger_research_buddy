from typing import List, Optional
from pydantic import BaseModel, Field

class Publication(BaseModel):
    """Schema for a research publication."""
    title: str
    year: Optional[int] = None
    venue: Optional[str] = None
    citations: Optional[int] = 0
    url: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None

class Faculty(BaseModel):
    """Schema for a faculty member."""
    id: Optional[str] = None  # Canonical ID (e.g., faculty_12345)
    name: str
    title: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    profile_url: Optional[str] = None
    image_url: Optional[str] = None
    college: Optional[str] = None
    
    # Research Info
    research_interests: List[str] = Field(default_factory=list)
    research_areas: List[str] = Field(default_factory=list)
    
    # Scholar Data
    scholar_id: Optional[str] = None
    citations: Optional[int] = 0
    h_index: Optional[int] = 0
    i10_index: Optional[int] = 0
    
    # Publications
    publications: List[Publication] = Field(default_factory=list)
    
    # Metadata
    source: str = "rit_website"  # rit_website, google_scholar, manual
    last_updated: str = None
