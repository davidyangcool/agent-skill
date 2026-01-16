# Agent Skill CLI

🎯 **The command-line interface for modern AI agents.** Manage, install, and execute skills directly from your terminal.

Part of [SkillMaster](https://skillmaster.cc/cli).

## 📦 Installation

The easiest way to get started. Requires Python 3.9+.

```bash
pip install agent-skill
```

## ⚡ Quick Start

```bash
# Search for skills
skill search "document processing"

# View skill details
skill show pdf

# Install a skill (interactive agent selection)
skill install pdf

# List installed skills
skill list
```

## 🤖 Supported Agents

Agent Skill supports **5 major AI coding agents** with automatic detection:

| Agent | Local Path | Global Path |
|-------|------------|-------------|
| **OpenCode** | `.opencode/skill/` | `~/.config/opencode/skill/` |
| **Claude Code** | `.claude/skills/` | `~/.claude/skills/` |
| **Codex** | `.codex/skills/` | `~/.codex/skills/` |
| **Cursor** | `.cursor/skills/` | `~/.cursor/skills/` |
| **Antigravity** | `.agent/skills/` | `~/.gemini/antigravity/skills/` |

During installation, `skill install` will:
1. Auto-detect which agents are present in your project
2. Show an interactive multi-select menu
3. Install the skill to all selected agents

## 🚀 Commands Showcase

### 🔍 Search (`search`, `-s`)

Find the perfect skill for your agent.

```bash
skill search "pdf processor"
skill -s "markdown"
skill search python --limit 10
```

### ℹ️ Show (`show`, `info`)

View comprehensive information about a skill, including rating, downloads, tags, and package structure.

```bash
skill show pdf
skill show notebooklm
```

### 📦 Install (`install`)

Interactive multi-agent installation with a single download.

```bash
# Interactive: auto-detect agents and let you choose
skill install pdf

# Install to a specific agent only
skill install pdf -a claude
skill install pdf --agent cursor

# Install to global directory
skill install notebooklm -g

# Install to custom path
skill install my-skill --path ./custom-dir/

# Force reinstall
skill install pdf --force
```

**Flags:**
- `-a, --agent AGENT`: Install to a specific agent only (`opencode`, `claude`, `codex`, `cursor`, `antigravity`)
- `-g, --global`: Install to global paths instead of local project
- `-p, --path PATH`: Custom installation path
- `-f, --force`: Overwrite if already installed

### 📋 List (`list`, `ls`)

List and manage your installed skills.

```bash
skill list
skill ls
```

### 🌐 Open (`open`)

Open the skill's source code or documentation in your browser.

```bash
skill open notebooklm
skill open pdf
```

### ⚙️ Config (`config`)

View and edit settings.

```bash
skill config
```

### 🗑️ Uninstall (`uninstall`)

Remove an installed skill.

```bash
skill uninstall pdf
skill uninstall notebooklm -y  # skip confirmation
```

## 💡 Command Cheat Sheet

| Command | Alias | Description | Example |
|---------|-------|-------------|---------|
| `search` | `-s` | Search for skills | `skill search pdf` |
| `show` | `info` | View skill details | `skill show pdf` |
| `install` | - | Install a skill | `skill install pdf` |
| `uninstall` | - | Remove a skill | `skill uninstall pdf` |
| `list` | `ls` | List installed skills | `skill list` |
| `open` | - | Open source in browser | `skill open pdf` |
| `config` | - | View configuration | `skill config` |

## 📂 Directory Structure

### Config & Registry

```text
~/.claude/skill-cli/
├── config.json       # User configuration
└── installed.json    # Installed skills registry
```

### Skill Installation Paths

**Local (default)** - installed in your project directory:
```text
your-project/
├── .opencode/skill/pdf/     # OpenCode
├── .claude/skills/pdf/      # Claude Code
├── .codex/skills/pdf/       # Codex
├── .cursor/skills/pdf/      # Cursor
└── .agent/skills/pdf/       # Antigravity
```

**Global (`-g` flag)** - installed in your home directory:
```text
~/
├── .config/opencode/skill/pdf/         # OpenCode
├── .claude/skills/pdf/                 # Claude Code
├── .codex/skills/pdf/                  # Codex
├── .cursor/skills/pdf/                 # Cursor
└── .gemini/antigravity/skills/pdf/     # Antigravity
```

## 🤖 MCP Server (AI Agent Integration)

Agent Skill can run as an **MCP (Model Context Protocol) Server**, allowing AI agents like Claude, Gemini, and Cursor to directly manage skills.

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_skills` | Search for skills by keywords |
| `get_skill_detail` | Get detailed information about a skill |
| `install_skill` | Download and install a skill |
| `uninstall_skill` | Remove an installed skill |
| `list_installed_skills` | List all installed skills |
| `get_skill_source_url` | Get GitHub source URL for a skill |

### Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skill-mcp": {
      "command": "skill-mcp",
      "args": []
    }
  }
}
```

### Configure Cursor IDE

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "skill-mcp": {
      "command": "skill-mcp",
      "args": []
    }
  }
}
```

### Configure Claude Code (CLI)

```bash
# Add to user config
claude mcp add skill-mcp /path/to/skill-mcp --scope user

# Or add to project config
claude mcp add skill-mcp skill-mcp --scope project
```

### Test with MCP Inspector

```bash
# Run the MCP dev inspector
mcp dev agent_skill/mcp_server.py
```

## 🛠️ Development

```bash
# Clone the repository
git clone https://github.com/anthropics/agent-skill.git
cd agent-skill

# Install in editable mode
pip install -e .

# Run CLI directly
skill search "test"
```

## 📄 License

MIT
