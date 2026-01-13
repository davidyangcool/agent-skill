"""
Data models for Skill CLI
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Tag:
    """Skill tag"""
    id: str
    name: str
    usage_count: int = 0


@dataclass
class Skill:
    """Skill data from API"""
    id: str
    name: str
    description: Optional[str] = None
    skill_content: Optional[str] = None
    source_url: Optional[str] = None
    github_stars: int = 0
    average_rating: float = 0.0
    rating_count: int = 0
    download_count: int = 0
    comment_count: int = 0
    tutorial_count: int = 0
    status: str = "published"
    created_at: int = 0
    directory_structure: Optional[str] = None
    file_size_mb: float = 0.0
    tags: List[Tag] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        """Create Skill from API response dict"""
        tags = []
        if "tags" in data and data["tags"]:
            tags = [Tag(**t) for t in data["tags"]]
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            skill_content=data.get("skill_content"),
            source_url=data.get("source_url"),
            github_stars=data.get("github_stars", 0),
            average_rating=data.get("average_rating", 0.0),
            rating_count=data.get("rating_count", 0),
            download_count=data.get("download_count", 0),
            comment_count=data.get("comment_count", 0),
            tutorial_count=data.get("tutorial_count", 0),
            status=data.get("status", "published"),
            created_at=data.get("created_at", 0),
            directory_structure=data.get("directory_structure"),
            file_size_mb=data.get("file_size_mb", 0.0),
            tags=tags,
        )


@dataclass
class InstalledSkill:
    """Locally installed skill record"""
    id: str
    name: str
    installed_at: str  # ISO format datetime
    path: str
    version: Optional[str] = None
    source_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "installed_at": self.installed_at,
            "path": self.path,
            "version": self.version,
            "source_url": self.source_url,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InstalledSkill":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            installed_at=data.get("installed_at", ""),
            path=data.get("path", ""),
            version=data.get("version"),
            source_url=data.get("source_url"),
        )
