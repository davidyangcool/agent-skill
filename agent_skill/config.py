"""
Configuration management for Skill CLI
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

# Default configuration
DEFAULT_API_BASE_URL = "https://skillmaster.cc"

# Config directory (always in home)
DEFAULT_CONFIG_DIR = Path.home() / ".claude" / "skill-cli"

# Skills directories
GLOBAL_SKILLS_DIR = Path.home() / ".claude" / "skills"  # ~/.claude/skills
LOCAL_SKILLS_SUBDIR = ".claude/skills"  # ./.claude/skills (relative to cwd)

CONFIG_FILE = "config.json"
INSTALLED_FILE = "installed.json"


@dataclass
class Config:
    """User configuration"""
    api_base_url: str = DEFAULT_API_BASE_URL
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(
            api_base_url=data.get("api_base_url", DEFAULT_API_BASE_URL),
        )


def get_config_dir() -> Path:
    """Get or create the config directory"""
    config_dir = DEFAULT_CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_local_skills_dir() -> Path:
    """
    Get the local skills directory (relative to current working directory).
    Returns: ./.claude/skills/
    """
    local_dir = Path.cwd() / LOCAL_SKILLS_SUBDIR
    return local_dir


def get_global_skills_dir() -> Path:
    """
    Get the global skills directory (in home directory).
    Returns: ~/.claude/skills/
    """
    return GLOBAL_SKILLS_DIR


def get_skills_dir(global_install: bool = False) -> Path:
    """
    Get skills directory based on global flag.
    
    Args:
        global_install: If True, return global dir (~/.claude/skills)
                       If False, return local dir (./.claude/skills)
    
    Returns:
        Path to skills directory (creates if not exists)
    """
    if global_install:
        skills_dir = get_global_skills_dir()
    else:
        skills_dir = get_local_skills_dir()
    
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


def load_config() -> Config:
    """Load configuration from file or return defaults"""
    config_file = get_config_dir() / CONFIG_FILE
    
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Config.from_dict(data)
        except (json.JSONDecodeError, IOError):
            pass
    
    return Config()


def save_config(config: Config) -> None:
    """Save configuration to file"""
    config_file = get_config_dir() / CONFIG_FILE
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)


def load_installed() -> Dict[str, Any]:
    """Load installed skills registry"""
    installed_file = get_config_dir() / INSTALLED_FILE
    
    if installed_file.exists():
        try:
            with open(installed_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {}


def save_installed(installed: Dict[str, Any]) -> None:
    """Save installed skills registry"""
    installed_file = get_config_dir() / INSTALLED_FILE
    
    with open(installed_file, "w", encoding="utf-8") as f:
        json.dump(installed, f, indent=2, ensure_ascii=False)


def add_installed_skill(name: str, skill_data: dict) -> None:
    """Add a skill to the installed registry"""
    installed = load_installed()
    installed[name] = skill_data
    save_installed(installed)


def remove_installed_skill(name: str) -> bool:
    """Remove a skill from the installed registry"""
    installed = load_installed()
    if name in installed:
        del installed[name]
        save_installed(installed)
        return True
    return False


def get_installed_skill(name: str) -> dict | None:
    """Get an installed skill by name"""
    installed = load_installed()
    return installed.get(name)
