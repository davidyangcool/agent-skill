"""
SkillMaster MCP Server - Enable AI agents to manage skills

This module wraps the agent-skill CLI as an MCP (Model Context Protocol) server,
allowing AI agents like Claude, Gemini, and Cursor to directly search, install,
and manage skills from SkillMaster.

Usage:
    # Run as MCP server (stdio transport)
    skill-mcp
    
    # Or run directly
    python -m agent_skill.mcp_server
"""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .api import SkillMasterAPI
from .config import (
    load_config,
    load_installed,
    get_installed_skill,
    add_installed_skill,
    remove_installed_skill,
    get_skills_dir,
    get_local_skills_dir,
    get_global_skills_dir,
)

# Initialize MCP server
mcp = FastMCP("skill-mcp")


# ===========================================
# MCP Tools
# ===========================================

@mcp.tool()
def search_skills(query: str, limit: int = 20) -> str:
    """
    Search for AI agent skills by keywords.
    
    Args:
        query: Search keywords (e.g., "pdf processor", "web scraper", "markdown")
        limit: Maximum number of results to return (default: 20, max: 50)
    
    Returns:
        JSON array of matching skills with id, name, description, rating, and downloads
    """
    limit = min(limit, 50)  # Cap at 50
    
    try:
        with SkillMasterAPI() as api:
            skills = api.search(query)[:limit]
            results = [{
                "id": s.id,
                "name": s.name,
                "description": s.description or "",
                "rating": s.average_rating,
                "downloads": s.download_count,
                "github_stars": s.github_stars,
            } for s in skills]
            
            if not results:
                return json.dumps({"message": f"No skills found for query: {query}", "results": []})
            
            return json.dumps({"count": len(results), "results": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_skill_detail(skill_id: str) -> str:
    """
    Get detailed information about a specific skill.
    
    Args:
        skill_id: The skill ID (64-char SHA-256 hash) or skill name
    
    Returns:
        JSON object with full skill details including SKILL.md content and package structure
    """
    try:
        with SkillMasterAPI() as api:
            skill = None
            
            # Check if it's a full SHA-256 ID (64 hex chars)
            if len(skill_id) == 64 and all(c in '0123456789abcdef' for c in skill_id.lower()):
                skill = api.get_skill(skill_id)
            else:
                # Search by name
                results = api.search(skill_id)
                if results:
                    # Try exact name match first
                    for s in results:
                        if s.name.lower() == skill_id.lower():
                            skill = api.get_skill(s.id)
                            break
                    # If no exact match, use first result
                    if not skill and results:
                        skill = api.get_skill(results[0].id)
            
            if not skill:
                return json.dumps({"error": f"Skill not found: {skill_id}"})
            
            return json.dumps({
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "skill_content": skill.skill_content,
                "source_url": skill.source_url,
                "rating": skill.average_rating,
                "rating_count": skill.rating_count,
                "downloads": skill.download_count,
                "github_stars": skill.github_stars,
                "file_size_mb": skill.file_size_mb,
                "directory_structure": skill.directory_structure,
                "tags": [{"id": t.id, "name": t.name} for t in skill.tags] if skill.tags else [],
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def install_skill(skill_id: str, global_install: bool = False, force: bool = False) -> str:
    """
    Download and install a skill to the local skills directory.
    
    Args:
        skill_id: The skill ID (64-char SHA-256) or skill name to install
        global_install: If True, install to ~/.claude/skills/ (global directory).
                        If False (default), install to ./.claude/skills/ (project-local).
        force: If True, overwrite existing installation
    
    Returns:
        Installation result with success status and path information
    """
    try:
        with SkillMasterAPI() as api:
            skill = None
            
            # Resolve skill ID
            if len(skill_id) == 64 and all(c in '0123456789abcdef' for c in skill_id.lower()):
                skill = api.get_skill(skill_id)
            else:
                # Search by name
                results = api.search(skill_id)
                if results:
                    for s in results:
                        if s.name.lower() == skill_id.lower():
                            skill = api.get_skill(s.id)
                            break
                    if not skill and results:
                        skill = api.get_skill(results[0].id)
            
            if not skill:
                return json.dumps({"success": False, "error": f"Skill not found: {skill_id}"})
            
            # Check if already installed
            existing = get_installed_skill(skill.name)
            if existing and not force:
                return json.dumps({
                    "success": False,
                    "error": f"Skill '{skill.name}' is already installed at {existing.get('path')}",
                    "hint": "Use force=True to reinstall"
                })
            
            # Determine install path
            install_dir = get_skills_dir(global_install=global_install) / skill.name
            
            # Create temp download path
            temp_zip = install_dir.parent / f".{skill.name}.zip.tmp"
            
            # Ensure parent directory exists
            install_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Download
            api.download_skill(skill.id, temp_zip)
            
            # Remove existing directory if force
            if install_dir.exists():
                shutil.rmtree(install_dir)
            
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            try:
                with zipfile.ZipFile(temp_zip, 'r') as zf:
                    zf.extractall(install_dir)
            except zipfile.BadZipFile:
                if temp_zip.exists():
                    temp_zip.unlink()
                return json.dumps({"success": False, "error": "Downloaded file is not a valid ZIP archive"})
            
            # Clean up temp file
            if temp_zip.exists():
                temp_zip.unlink()
            
            # Record installation
            installed_data = {
                "id": skill.id,
                "name": skill.name,
                "installed_at": datetime.now().isoformat(),
                "path": str(install_dir),
                "source_url": skill.source_url,
            }
            add_installed_skill(skill.name, installed_data)
            
            return json.dumps({
                "success": True,
                "message": f"Successfully installed {skill.name}",
                "name": skill.name,
                "path": str(install_dir),
                "global": global_install
            })
            
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def uninstall_skill(name: str) -> str:
    """
    Remove an installed skill.
    
    Args:
        name: Name of the skill to uninstall
    
    Returns:
        Uninstallation result with success status
    """
    try:
        # Check if installed
        installed = get_installed_skill(name)
        
        if not installed:
            return json.dumps({
                "success": False,
                "error": f"Skill '{name}' is not installed",
                "hint": "Use list_installed_skills to see installed skills"
            })
        
        install_path = Path(installed.get("path", ""))
        
        # Remove directory
        if install_path.exists():
            shutil.rmtree(install_path)
        
        # Remove from registry
        remove_installed_skill(name)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully uninstalled {name}",
            "removed_path": str(install_path)
        })
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def list_installed_skills() -> str:
    """
    List all locally installed skills.
    
    Returns:
        JSON array of installed skills with name, path, install date, and source URL
    """
    try:
        installed = load_installed()
        
        if not installed:
            return json.dumps({
                "message": "No skills installed yet",
                "hint": "Use install_skill to install a skill",
                "skills": []
            })
        
        skills = [{
            "name": data.get("name"),
            "path": data.get("path"),
            "installed_at": data.get("installed_at"),
            "source_url": data.get("source_url"),
            "id": data.get("id")
        } for data in installed.values()]
        
        return json.dumps({
            "count": len(skills),
            "skills": skills
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_skill_source_url(skill_id: str) -> str:
    """
    Get the GitHub source URL for a skill.
    
    Args:
        skill_id: The skill ID or name
    
    Returns:
        JSON object with skill name and source URL
    """
    try:
        with SkillMasterAPI() as api:
            skill = None
            
            if len(skill_id) == 64 and all(c in '0123456789abcdef' for c in skill_id.lower()):
                skill = api.get_skill(skill_id)
            else:
                results = api.search(skill_id)
                if results:
                    for s in results:
                        if s.name.lower() == skill_id.lower():
                            skill = api.get_skill(s.id)
                            break
                    if not skill and results:
                        skill = api.get_skill(results[0].id)
            
            if not skill:
                return json.dumps({"error": f"Skill not found: {skill_id}"})
            
            if not skill.source_url:
                return json.dumps({"error": f"Skill '{skill.name}' has no source URL"})
            
            return json.dumps({
                "name": skill.name,
                "source_url": skill.source_url
            })
            
    except Exception as e:
        return json.dumps({"error": str(e)})


# ===========================================
# MCP Resources (Read-only context)
# ===========================================

@mcp.resource("skill-mcp://installed")
def get_installed_resource() -> str:
    """Resource: List of all installed skills (read-only snapshot)"""
    installed = load_installed()
    return json.dumps(installed, indent=2)


@mcp.resource("skill-mcp://config")
def get_config_resource() -> str:
    """Resource: Current CLI configuration"""
    cfg = load_config()
    return json.dumps({
        "api_base_url": cfg.api_base_url,
        "local_skills_dir": str(get_local_skills_dir()),
        "global_skills_dir": str(get_global_skills_dir())
    }, indent=2)


# ===========================================
# Server Entry Point
# ===========================================

def main():
    """Run the MCP server with stdio transport"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
