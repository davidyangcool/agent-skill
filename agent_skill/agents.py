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
        "local_path": ".opencode/skills",
        "global_path": "~/.config/opencode/skills",
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
    "amp": {
        "name": "Amp",
        "local_path": ".agents/skills",
        "global_path": "~/.config/agents/skills",
        "detect_markers": [".agents"],
    },
    "kilocode": {
        "name": "Kilo Code",
        "local_path": ".kilocode/skills",
        "global_path": "~/.kilocode/skills",
        "detect_markers": [".kilocode"],
    },
    "roocode": {
        "name": "Roo Code",
        "local_path": ".roo/skills",
        "global_path": "~/.roo/skills",
        "detect_markers": [".roo"],
    },
    "goose": {
        "name": "Goose",
        "local_path": ".goose/skills",
        "global_path": "~/.config/goose/skills",
        "detect_markers": [".goose"],
    },
    "gemini": {
        "name": "Gemini CLI",
        "local_path": ".gemini/skills",
        "global_path": "~/.gemini/skills",
        "detect_markers": [".gemini"],
    },
    "copilot": {
        "name": "GitHub Copilot",
        "local_path": ".github/skills",
        "global_path": "~/.copilot/skills",
        "detect_markers": [".copilot", ".github"],
    },
    "clawdbot": {
        "name": "Clawdbot",
        "local_path": "skills",
        "global_path": "~/.clawdbot/skills",
        "detect_markers": [".clawdbot"],
    },
    "droid": {
        "name": "Droid",
        "local_path": ".factory/skills",
        "global_path": "~/.factory/skills",
        "detect_markers": [".factory"],
    },
    "windsurf": {
        "name": "Windsurf",
        "local_path": ".windsurf/skills",
        "global_path": "~/.codeium/windsurf/skills",
        "detect_markers": [".windsurf", ".codeium"],
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
