"""
Agent definitions and detection logic for multi-agent skill installation.

Supported agents:
- OpenCode
- Claude Code
- Codex
- Cursor
- Antigravity
"""

from pathlib import Path
from typing import List, Dict, Any


# Agent configuration (Claude Code first as default)
AGENTS: Dict[str, Dict[str, Any]] = {
    "claude": {
        "name": "Claude Code",
        "local_path": ".claude/skills",
        "global_path": "~/.claude/skills",
        "detect_markers": [".claude"],
    },
    "opencode": {
        "name": "OpenCode",
        "local_path": ".opencode/skill",
        "global_path": "~/.config/opencode/skill",
        "detect_markers": [".opencode"],
    },
    "codex": {
        "name": "Codex",
        "local_path": ".codex/skills",
        "global_path": "~/.codex/skills",
        "detect_markers": [".codex"],
    },
    "cursor": {
        "name": "Cursor",
        "local_path": ".cursor/skills",
        "global_path": "~/.cursor/skills",
        "detect_markers": [".cursor"],
    },
    "antigravity": {
        "name": "Antigravity",
        "local_path": ".agent/skills",
        "global_path": "~/.gemini/antigravity/skills",
        "detect_markers": [".agent", ".gemini"],
    },
}


def detect_agents(cwd: Path = None) -> List[str]:
    """
    Detect which agents are present in the current project directory.
    
    Returns a list of agent IDs that have their marker directories present.
    """
    if cwd is None:
        cwd = Path.cwd()
    
    detected = []
    for agent_id, config in AGENTS.items():
        for marker in config["detect_markers"]:
            marker_path = cwd / marker
            if marker_path.exists() and marker_path.is_dir():
                detected.append(agent_id)
                break
    
    return detected


def get_all_agent_ids() -> List[str]:
    """Get all supported agent IDs."""
    return list(AGENTS.keys())


def get_agent_name(agent_id: str) -> str:
    """Get the display name for an agent."""
    return AGENTS.get(agent_id, {}).get("name", agent_id)


def get_agent_local_path(agent_id: str) -> str:
    """Get the local install path pattern for an agent."""
    return AGENTS.get(agent_id, {}).get("local_path", ".claude/skills")


def get_agent_global_path(agent_id: str) -> str:
    """Get the global install path pattern for an agent."""
    return AGENTS.get(agent_id, {}).get("global_path", "~/.claude/skills")


def get_agent_install_path(agent_id: str, skill_name: str, global_install: bool = False, cwd: Path = None) -> Path:
    """
    Get the full install path for a skill to a specific agent.
    
    Args:
        agent_id: The agent identifier (e.g., "claude", "cursor")
        skill_name: The name of the skill being installed
        global_install: If True, use global path; otherwise use local path
        cwd: Current working directory (for local installs)
    
    Returns:
        Full Path to the skill installation directory
    """
    if cwd is None:
        cwd = Path.cwd()
    
    agent = AGENTS.get(agent_id)
    if not agent:
        # Default to Claude Code if unknown agent
        agent = AGENTS["claude"]
    
    if global_install:
        base_path = Path(agent["global_path"]).expanduser()
    else:
        base_path = cwd / agent["local_path"]
    
    return base_path / skill_name
