"""SQLite database for structured research data storage."""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from rich.console import Console
from ..utils.config import DATA_DIR

console = Console()

DB_PATH = DATA_DIR / "tiger_research.db"


@contextmanager
def get_connection():
    """Get a database connection context manager."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with schema."""
    console.print("[bold blue]📦 Initializing SQLite database...[/]")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Faculty table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                title TEXT,
                department TEXT,
                email TEXT,
                profile_url TEXT,
                bio TEXT,
                research_interests TEXT,
                citations INTEGER DEFAULT 0,
                h_index INTEGER DEFAULT 0,
                i10_index INTEGER DEFAULT 0,
                scholar_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Publications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                year TEXT,
                venue TEXT,
                citations INTEGER DEFAULT 0,
                abstract TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Faculty-Publication junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty_publications (
                faculty_id INTEGER,
                publication_id INTEGER,
                is_primary_author BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (faculty_id, publication_id),
                FOREIGN KEY (faculty_id) REFERENCES faculty(id),
                FOREIGN KEY (publication_id) REFERENCES publications(id)
            )
        """)
        
        # Research areas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT,
                description TEXT,
                parent_area_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_area_id) REFERENCES research_areas(id)
            )
        """)
        
        # Tags table with categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT,
                parent_tag_id INTEGER,
                description TEXT,
                FOREIGN KEY (parent_tag_id) REFERENCES tags(id)
            )
        """)
        
        # Faculty-Tag junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty_tags (
                faculty_id INTEGER,
                tag_id INTEGER,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'auto',
                PRIMARY KEY (faculty_id, tag_id),
                FOREIGN KEY (faculty_id) REFERENCES faculty(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)
        
        # Publication-Tag junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publication_tags (
                publication_id INTEGER,
                tag_id INTEGER,
                confidence REAL DEFAULT 1.0,
                PRIMARY KEY (publication_id, tag_id),
                FOREIGN KEY (publication_id) REFERENCES publications(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)
        
        # Research Area-Tag junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_area_tags (
                research_area_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (research_area_id, tag_id),
                FOREIGN KEY (research_area_id) REFERENCES research_areas(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)
        
        # Faculty-Research Area junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty_research_areas (
                faculty_id INTEGER,
                research_area_id INTEGER,
                PRIMARY KEY (faculty_id, research_area_id),
                FOREIGN KEY (faculty_id) REFERENCES faculty(id),
                FOREIGN KEY (research_area_id) REFERENCES research_areas(id)
            )
        """)
        
        # Projects table (for future crawling)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                url TEXT,
                faculty_id INTEGER,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faculty_id) REFERENCES faculty(id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faculty_name ON faculty(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_publications_title ON publications(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)")
        
        conn.commit()
    
    console.print(f"[green]✓ Database initialized at {DB_PATH}[/]")


class ResearchDatabase:
    """Interface for the research database."""
    
    def __init__(self):
        init_database()
    
    def add_faculty(self, name: str, **kwargs) -> int:
        """Add or update a faculty member."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute("SELECT id FROM faculty WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if row:
                # Update existing
                updates = ", ".join(f"{k} = ?" for k in kwargs.keys())
                if updates:
                    cursor.execute(
                        f"UPDATE faculty SET {updates}, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                        (*kwargs.values(), name)
                    )
                conn.commit()
                return row["id"]
            else:
                # Insert new
                cols = ["name"] + list(kwargs.keys())
                placeholders = ", ".join(["?"] * len(cols))
                cursor.execute(
                    f"INSERT INTO faculty ({', '.join(cols)}) VALUES ({placeholders})",
                    (name, *kwargs.values())
                )
                conn.commit()
                return cursor.lastrowid
    
    def add_publication(self, title: str, faculty_id: int = None, **kwargs) -> int:
        """Add a publication and link to faculty."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute("SELECT id FROM publications WHERE title = ?", (title,))
            row = cursor.fetchone()
            
            if row:
                pub_id = row["id"]
            else:
                cols = ["title"] + list(kwargs.keys())
                placeholders = ", ".join(["?"] * len(cols))
                cursor.execute(
                    f"INSERT INTO publications ({', '.join(cols)}) VALUES ({placeholders})",
                    (title, *kwargs.values())
                )
                pub_id = cursor.lastrowid
            
            # Link to faculty if provided
            if faculty_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO faculty_publications (faculty_id, publication_id) VALUES (?, ?)",
                    (faculty_id, pub_id)
                )
            
            conn.commit()
            return pub_id
    
    def add_tag(self, name: str, category: str = None, parent_id: int = None) -> int:
        """Add a tag."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO tags (name, category, parent_tag_id) VALUES (?, ?, ?)",
                (name.lower(), category, parent_id)
            )
            conn.commit()
            
            cursor.execute("SELECT id FROM tags WHERE name = ?", (name.lower(),))
            return cursor.fetchone()["id"]
    
    def add_faculty_tag(self, faculty_id: int, tag_id: int, confidence: float = 1.0, source: str = "auto"):
        """Link a tag to faculty."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO faculty_tags (faculty_id, tag_id, confidence, source) VALUES (?, ?, ?, ?)",
                (faculty_id, tag_id, confidence, source)
            )
            conn.commit()
    
    def get_all_tags(self) -> list[dict]:
        """Get all tags."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags ORDER BY category, name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_faculty_with_tags(self, faculty_id: int) -> dict:
        """Get faculty with their tags."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM faculty WHERE id = ?", (faculty_id,))
            faculty = dict(cursor.fetchone()) if cursor.fetchone() else None
            
            if faculty:
                cursor.execute("""
                    SELECT t.* FROM tags t
                    JOIN faculty_tags ft ON t.id = ft.tag_id
                    WHERE ft.faculty_id = ?
                """, (faculty_id,))
                faculty["tags"] = [dict(row) for row in cursor.fetchall()]
            
            return faculty
    
    def search_by_tag(self, tag_name: str) -> list[dict]:
        """Search faculty by tag."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.* FROM faculty f
                JOIN faculty_tags ft ON f.id = ft.faculty_id
                JOIN tags t ON ft.tag_id = t.id
                WHERE t.name LIKE ?
            """, (f"%{tag_name.lower()}%",))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            for table in ["faculty", "publications", "research_areas", "tags"]:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()["count"]
            
            return stats
