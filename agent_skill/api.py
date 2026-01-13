"""
API client for SkillMaster backend
"""

import httpx
from typing import List, Optional
from pathlib import Path

from .models import Skill
from .config import load_config


class SkillMasterAPI:
    """API client for SkillMaster backend"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        config = load_config()
        self.base_url = (base_url or config.api_base_url).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized HTTP client"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "SkillCLI/0.1.0",
                    "Accept": "application/json",
                },
            )
        return self._client
    
    def close(self) -> None:
        """Close the HTTP client"""
        if self._client is not None:
            self._client.close()
            self._client = None
    
    def __enter__(self) -> "SkillMasterAPI":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    def search(self, query: str) -> List[Skill]:
        """
        Search for skills by query string.
        
        Args:
            query: Search query (supports keywords and phrases)
        
        Returns:
            List of matching Skill objects
        """
        response = self.client.get(
            "/api/skills/search",
            params={"q": query},
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Handle both list response and object with 'results' key
        if isinstance(data, list):
            return [Skill.from_dict(item) for item in data]
        elif isinstance(data, dict) and "results" in data:
            return [Skill.from_dict(item) for item in data["results"]]
        else:
            return []
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        Get skill details by ID.
        
        Args:
            skill_id: SHA-256 skill ID (64 hex chars) or partial match
        
        Returns:
            Skill object if found, None otherwise
        """
        response = self.client.get(f"/api/skills/{skill_id}")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return Skill.from_dict(response.json())
    
    def get_skills(self, page: int = 1, limit: int = 20, sort: str = "created") -> List[Skill]:
        """
        Get paginated list of all skills.
        
        Args:
            page: Page number (1-indexed)
            limit: Items per page (max 100)
            sort: Sort order ('created' or 'rating')
        
        Returns:
            List of Skill objects
        """
        response = self.client.get(
            "/api/skills",
            params={"page": page, "limit": limit, "sort": sort},
        )
        response.raise_for_status()
        
        return [Skill.from_dict(item) for item in response.json()]
    
    def download_skill(self, skill_id: str, dest_path: Path) -> Path:
        """
        Download a skill package as ZIP file.
        
        Args:
            skill_id: SHA-256 skill ID
            dest_path: Destination file path for the ZIP
        
        Returns:
            Path to the downloaded ZIP file
        
        Raises:
            httpx.HTTPStatusError: If download fails
        """
        # Stream download for large files
        with self.client.stream("GET", f"/download/{skill_id}") as response:
            response.raise_for_status()
            
            # Get total size from Content-Length header (if available)
            total_size = int(response.headers.get("content-length", 0))
            
            # Ensure parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file in chunks
            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        
        return dest_path
    
    def download_skill_with_progress(
        self, 
        skill_id: str, 
        dest_path: Path,
        progress_callback=None
    ) -> Path:
        """
        Download a skill package with progress callback.
        
        Args:
            skill_id: SHA-256 skill ID
            dest_path: Destination file path for the ZIP
            progress_callback: Callable(downloaded_bytes, total_bytes) for progress updates
        
        Returns:
            Path to the downloaded ZIP file
        """
        with self.client.stream("GET", f"/download/{skill_id}") as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        
        return dest_path


# Singleton instance for convenience
_api_instance: Optional[SkillMasterAPI] = None


def get_api() -> SkillMasterAPI:
    """Get or create the global API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = SkillMasterAPI()
    return _api_instance
