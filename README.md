# Agent Skill CLI

🎯 **The command-line interface for modern AI agents.** Manage, install, and execute skills directly from your terminal.

Part of [SkillMaster](https://skillmaster.cc).

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

# Install a skill
skill install pdf

# List installed skills
skill list
```

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

One-command installation with dependency resolution.

```bash
# Install to local project (./.claude/skills/)
skill install pdf

# Install to global directory (~/.claude/skills/)
skill install notebooklm -g

# Install to custom path
skill install my-skill --path ./custom-dir/

# Force reinstall
skill install pdf --force
```

**Flags:**
- `-g, --global`: Install to `~/.claude/skills/`
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

```text
~/.claude/
├── skill-cli/
│   ├── config.json       # User configuration
│   └── installed.json    # Installed skills registry
└── skills/               # Global skills (with -g flag)
    ├── notebooklm/
    └── pdf/

./.claude/skills/         # Local project skills (default)
├── docx/
└── xlsx/
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
git clone https://github.com/yourusername/agent-skill.git
cd agent-skill

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run CLI directly
python -m agent_skill.cli search "test"
```

## 📄 License

MIT
