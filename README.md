# Agent Skill CLI

🎯 A command-line tool for managing AI agent skills from [SkillMaster](https://skillmaster.cc).

## Installation

```bash
# Install from source
cd agent-skill
pip install -e .

# Or install with pip (when published)
pip install agent-skill
```

## Quick Start

```bash
# Search for skills
skill search "document processing"
skill -s "python"

# View skill details
skill show pdf

# Open skill source in browser
skill open notebooklm

# Install a skill (local project)
skill install pdf

# Install a skill (global)
skill install notebooklm -g

# List installed skills
skill list

# Uninstall a skill
skill uninstall pdf
```

## Commands

### Search (`search`, `-s`)

Search for skills by keywords:

```bash
skill search "pdf processor"
skill -s "markdown"
skill search python --limit 10
```

### Show (`show`, `info`)

View detailed information about a skill:

```bash
skill show pdf
skill show notebooklm
skill info ui-ux-pro-max
```

Displays: name, rating, downloads, tags, source URL, description, and package structure.

### Open

Open skill's source URL in browser:

```bash
skill open notebooklm
skill open pdf
```

### Install

Download and install a skill:

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

| Flag | Description |
|------|-------------|
| `-g, --global` | Install to `~/.claude/skills/` |
| `-p, --path PATH` | Custom installation path |
| `-f, --force` | Overwrite if already installed |

### Uninstall

Remove an installed skill:

```bash
skill uninstall pdf
skill uninstall notebooklm -y  # skip confirmation
```

### List (`list`, `ls`)

List all installed skills:

```bash
skill list
skill ls
```

### Config

Show current configuration:

```bash
skill config
```

Output:
```
⚙️  Skill CLI Configuration

  API Base URL:   https://skillmaster.cc
  Config Dir:     ~/.claude/skill-cli
  Local Skills:   ./.claude/skills  (default)
  Global Skills:  ~/.claude/skills  (use -g)
  Installed:      3 skill(s)
  Version:        0.1.0
```

## Directory Structure

```
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

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run CLI directly
python -m agent_skill.cli search "test"
```

## License

MIT
