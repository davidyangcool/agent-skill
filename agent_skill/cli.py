"""
Skill CLI - Main command-line interface

Commands:
    skill search <query>     Search for skills
    skill -s <query>         Short alias for search
    skill show <id>          Show skill details
    skill install <id>       Install a skill
    skill uninstall <name>   Uninstall a skill
    skill list               List installed skills
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional

import click
import httpx

from . import __version__
from .api import SkillMasterAPI, get_api
from .config import (
    load_config, 
    get_skills_dir,
    get_local_skills_dir,
    get_global_skills_dir,
    load_installed, 
    add_installed_skill, 
    remove_installed_skill,
    get_installed_skill,
)
from .models import Skill, InstalledSkill
from .display import (
    console,
    display_search_results,
    display_skill_detail,
    display_installed_list,
    get_download_progress,
    print_success,
    print_error,
    print_info,
    print_warning,
)


# Context settings for CLI
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('-v', '--version', is_flag=True, help='Show version and exit.')
@click.option('-s', '--search', 'search_query', metavar='QUERY', help='Search for skills (shortcut).')
@click.pass_context
def main(ctx, version: bool, search_query: Optional[str]):
    """
    🎯 Agent Skill CLI - Manage AI agent skills from SkillMaster
    
    \b
    Examples:
        skill search "document"      Search for skills
        skill -s "python"            Short search command
        skill show <id>              View skill details
        skill install <id>           Install a skill
        skill list                   List installed skills
    
    \b
    Documentation: https://skillmaster.cc
    """
    if version:
        console.print(f"[bold cyan]skill-cli[/bold cyan] version [green]{__version__}[/green]")
        ctx.exit(0)
    
    # Handle -s shortcut for search
    if search_query:
        ctx.invoke(search, query=search_query)
        ctx.exit(0)
    
    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument('query')
@click.option('--limit', '-l', default=20, help='Maximum results to show.')
@click.option('--no-interactive', '-n', is_flag=True, help='Disable interactive mode.')
def search(query: str, limit: int, no_interactive: bool):
    """
    Search for skills by keywords.
    
    \b
    Interactive mode (default):
        Search Results:
            ↑/↓: Navigate results
            Enter: View skill details
            q: Quit
        
        Skill Details:
            i: Install skill
            b/Esc: Back to results
            q: Quit
    
    \b
    Examples:
        skill search document
        skill search "python automation"
        skill search pdf --limit 10
        skill search pdf -n              # Non-interactive mode
    """
    console.print(f"\n[dim]🔍 Searching for '[bold]{query}[/bold]'...[/dim]")
    
    try:
        with SkillMasterAPI() as api:
            skills = api.search(query)
            
            # Limit results
            if len(skills) > limit:
                skills = skills[:limit]
            
            interactive = not no_interactive
            current_index = 0  # Track current position
            
            # Interactive loop: search -> detail -> install/back
            while True:
                # Display search results (interactive or not), starting at current_index
                selected_skill, current_index = display_search_results(
                    skills, query, interactive=interactive, initial_index=current_index
                )
                
                if not selected_skill:
                    # User quit or non-interactive mode
                    break
                
                # Fetch full skill details
                console.print()  # Clear line after Live display
                full_skill = api.get_skill(selected_skill.id)
                
                if not full_skill:
                    print_error(f"Could not load skill details: {selected_skill.name}")
                    continue
                
                # Show skill details with interactive options (has_back=True for search)
                action = display_skill_detail(full_skill, interactive=interactive, has_back=True)
                
                if action == 'install':
                    # Perform installation
                    _do_install_skill(api, full_skill)
                    # After install, return to list for more browsing
                    console.print("\n[dim]🔙 Returning to search results...[/dim]")
                    continue
                elif action == 'view_files':
                    # Show full directory tree
                    if full_skill.directory_structure:
                        console.clear()
                        from .display import display_directory_tree, _read_key
                        
                        try:
                            dir_data = json.loads(full_skill.directory_structure) if isinstance(full_skill.directory_structure, str) else full_skill.directory_structure
                            display_directory_tree(dir_data, full_skill.name)
                        except:
                            console.print("[red]Could not parse directory structure.[/red]")
                            
                        console.print("\n[dim]Press any key to return...[/dim]")
                        _read_key()
                    else:
                         console.print("[yellow]No directory structure available.[/yellow]")
                         
                    # Re-show detail view by looping
                    # We need to hack the loop slightly or just let it continue to show list then re-select?
                    # actually, 'continue' goes to list. Ideally we want to stay in detail.
                    # Simple fix: Let's just re-display detail immediately
                    action = display_skill_detail(full_skill, interactive=interactive, has_back=True)
                    if action == 'install':
                         _do_install_skill(api, full_skill)
                         continue
                    elif action == 'back':
                         continue
                    else:
                         break
                         
                elif action == 'back':
                    # Go back to search results at the same position
                    console.print("\n[dim]🔙 Returning to search results...[/dim]")
                    continue
                else:
                    # User quit (q or None)
                    break
            
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: HTTP {e.response.status_code}")
        if e.response.status_code == 500:
            print_info("The server encountered an error. Try again later.")
        sys.exit(1)
    except httpx.RequestError as e:
        print_error(f"Connection failed: {e}")
        print_info("Check your internet connection or API server availability.")
        sys.exit(1)


def _do_install_skill(api, skill: Skill, global_install: bool = False, path: Optional[str] = None, force: bool = True, agent: Optional[str] = None):
    """
    Internal function to install a skill with agent selection display.
    
    Flow:
    1. Show source and agent selection
    2. Download once to temp
    3. Install to all selected agents
    4. Cleanup temp and show summary
    """
    from .config import get_installed_skill, add_installed_skill
    from .agents import detect_agents, get_all_agent_ids, get_agent_name, get_agent_local_path, get_agent_global_path, get_agent_install_path, AGENTS
    from .display import display_install_step, display_agent_selection, display_scope_selection, display_install_summary
    import tempfile
    
    source_url = skill.source_url or f"https://skillmaster.cc/skill/{skill.id}"
    
    # Step 2: Agent selection (before download)
    if agent:
        # Specific agent requested - no interactive selection
        selected_agents = [agent] if agent in AGENTS else ["claude"]
    else:
        # Auto-detect for default selection, then let user choose
        detected = detect_agents()
        if not detected:
            detected = ["claude"]
        
        # Show agents with placeholder paths (will update after scope selection)
        agents_info = []
        for agent_id in get_all_agent_ids():
            agent_path = get_agent_local_path(agent_id)  # Show local by default
            agents_info.append({
                "id": agent_id,
                "name": get_agent_name(agent_id),
                "path": agent_path,
            })
        
        selected_agents = display_agent_selection(agents_info, detected, interactive=True)
        
        if not selected_agents:
            console.print()
            console.print("[yellow]Installation cancelled.[/yellow]")
            return
    
    console.print()
    
    # Step 3: Scope selection (Project or Global)
    if not global_install and not path:
        # Only show scope selection if not already specified via flags
        scope = display_scope_selection(interactive=True)
        
        if not scope:
            console.print()
            console.print("[yellow]Installation cancelled.[/yellow]")
            return
        
        global_install = (scope == "global")
    
    console.print()
    
    # Step 3: Download once to a temp file (in system temp dir to avoid leftover files)
    temp_dir = Path(tempfile.gettempdir())
    temp_zip = temp_dir / f"skill-{skill.id[:8]}.zip"
    
    # Use Panel to wrap download progress
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
    from .display import display_download_panel
    
    download_progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    )
    
    try:
        task = download_progress.add_task(f"Downloading {skill.name}", total=None)
        
        with Live(display_download_panel(skill.name, download_progress, source_url), console=console, refresh_per_second=10) as live:
            def update_progress(downloaded: int, total: int):
                if total > 0:
                    download_progress.update(task, total=total, completed=downloaded)
                else:
                    download_progress.update(task, advance=downloaded)
                live.update(display_download_panel(skill.name, download_progress, source_url))
            
            api.download_skill_with_progress(skill.id, temp_zip, update_progress)
    except Exception as e:
        console.print()
        print_error(f"Download failed: {e}")
        if temp_zip.exists():
            temp_zip.unlink()
        return
    
    # Step 4: Install to each selected agent
    install_results = []
    
    for agent_id in selected_agents:
        if path:
            install_dir = Path(path).expanduser() / skill.name
        else:
            install_dir = get_agent_install_path(agent_id, skill.name, global_install)
        
        try:
            # Remove existing directory if force
            if install_dir.exists():
                shutil.rmtree(install_dir)
            
            install_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                zf.extractall(install_dir)
            
            # Record installation
            installed_data = {
                "id": skill.id,
                "name": skill.name,
                "installed_at": datetime.now().isoformat(),
                "path": str(install_dir),
                "source_url": skill.source_url,
                "agent": agent_id,
            }
            add_installed_skill(f"{skill.name}@{agent_id}", installed_data)
            
            install_results.append({
                "agent_name": get_agent_name(agent_id),
                "path": str(install_dir),
                "success": True,
            })
        except Exception as e:
            install_results.append({
                "agent_name": get_agent_name(agent_id),
                "path": str(install_dir),
                "success": False,
            })
    
    # Step 5: Clean up temp file (in system temp dir, won't leave behind)
    if temp_zip.exists():
        temp_zip.unlink()
    
    # Step 6: Show summary with source URL in Panel title
    display_install_summary(skill.name, install_results, source_url)


@main.command()
@click.argument('skill_id')
def show(skill_id: str):
    """
    Show detailed information about a skill.
    
    \b
    SKILL_ID can be:
      - Full SHA-256 ID (64 characters)
      - Skill name (will search first)
    
    \b
    Examples:
        skill show docs-generator
        skill show a1b2c3d4e5f6...
    """
    try:
        with SkillMasterAPI() as api:
            skill = None
            
            # Check if it's a full SHA-256 ID (64 hex chars)
            if len(skill_id) == 64 and all(c in '0123456789abcdef' for c in skill_id.lower()):
                console.print(f"\n[dim]🔍 Looking up skill by ID...[/dim]")
                skill = api.get_skill(skill_id)
            else:
                # Search by name
                console.print(f"\n[dim]🔍 Searching for skill '{skill_id}'...[/dim]")
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
            
            if skill:
                # has_back=False since show command has no list to return to
                action = display_skill_detail(skill, has_back=False)
                
                # Handle interactive actions
                if action == 'install':
                    _do_install_skill(api, skill)
                # None means user quit (no 'back' action for show command)
            else:
                print_error(f"Skill not found: {skill_id}")
                print_info("Try searching with: skill search <keywords>")
                sys.exit(1)
                
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: HTTP {e.response.status_code}")
        sys.exit(1)
    except httpx.RequestError as e:
        print_error(f"Connection failed: {e}")
        sys.exit(1)


@main.command()
@click.argument('skill_id')
@click.option('--global', '-g', 'global_install', is_flag=True, help='Install to global directory.')
@click.option('--path', '-p', type=click.Path(), help='Custom installation path.')
@click.option('--force', '-f', is_flag=True, help='Overwrite if already installed.')
@click.option('--agent', '-a', type=str, help='Specific agent to install to (opencode, claude, codex, cursor, antigravity).')
def install(skill_id: str, global_install: bool, path: Optional[str], force: bool, agent: Optional[str]):
    """
    Download and install a skill.
    
    \b
    By default, detects available agents and installs to their skill directories.
    Use -a/--agent to specify a single agent, or -g/--global for global install.
    
    \b
    Supported agents:
      - opencode    (.opencode/skill/)
      - claude      (.claude/skills/)
      - codex       (.codex/skills/)
      - cursor      (.cursor/skills/)
      - antigravity (.agent/skills/)
    
    \b
    SKILL_ID can be:
      - Full SHA-256 ID (64 characters)
      - Skill name (will search first)
    
    \b
    Examples:
        skill install docs-generator          # Auto-detect agents
        skill install pdf-processor -g        # Install to global paths
        skill install my-skill -a claude      # Install only to Claude Code
        skill install pdf-processor --force   # Overwrite if exists
    """
    config = load_config()
    
    try:
        with SkillMasterAPI() as api:
            skill = None
            
            # Resolve skill ID
            console.print(f"\n[dim]🔍 Looking up skill: {skill_id}...[/dim]")
            
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
                print_error(f"Skill not found: {skill_id}")
                sys.exit(1)
            
            # Call the new install flow
            _do_install_skill(api, skill, global_install=global_install, path=path, force=force, agent=agent)
            
    except httpx.RequestError as e:
        print_error(f"Connection failed: {e}")
        sys.exit(1)


@main.command()
@click.argument('name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt.')
def uninstall(name: str, yes: bool):
    """
    Remove an installed skill.
    
    \b
    Examples:
        skill uninstall docs-generator
        skill uninstall pdf-processor -y
    """
    # Check if installed
    installed = get_installed_skill(name)
    
    if not installed:
        print_error(f"Skill '{name}' is not installed.")
        print_info("Use 'skill list' to see installed skills.")
        sys.exit(1)
    
    install_path = Path(installed.get("path", ""))
    
    # Confirm
    if not yes:
        console.print(f"\n[yellow]⚠️  This will remove:[/yellow]")
        console.print(f"   [bold]{name}[/bold]")
        console.print(f"   [dim]{install_path}[/dim]\n")
        
        if not click.confirm("Are you sure?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            sys.exit(0)
    
    # Remove directory
    console.print(f"\n[dim]🗑️  Removing {name}...[/dim]")
    
    if install_path.exists():
        try:
            shutil.rmtree(install_path)
        except OSError as e:
            print_error(f"Failed to remove directory: {e}")
            sys.exit(1)
    
    # Remove from registry
    remove_installed_skill(name)
    
    print_success(f"Successfully uninstalled {name}!")
    console.print()


@main.command('list')
@click.option('--path', '-p', is_flag=True, help='Show full installation paths.')
def list_skills(path: bool):
    """
    List all installed skills.
    
    \b
    Examples:
        skill list
        skill list --path
    """
    installed = load_installed()
    
    if not installed:
        console.print("\n[yellow]No skills installed yet.[/yellow]")
        console.print("[dim]Use 'skill search <query>' to find skills and 'skill install <name>' to install.[/dim]\n")
        return
    
    # Convert to InstalledSkill objects
    skills = [InstalledSkill.from_dict(data) for data in installed.values()]
    
    display_installed_list(skills)


@main.command()
def config():
    """
    Show current configuration.
    """
    from .config import load_config, get_config_dir, get_local_skills_dir, get_global_skills_dir
    
    cfg = load_config()
    config_dir = get_config_dir()
    local_dir = get_local_skills_dir()
    global_dir = get_global_skills_dir()
    installed = load_installed()
    
    console.print("\n[bold cyan]⚙️  Skill CLI Configuration[/bold cyan]\n")
    console.print(f"  [bold]API Base URL:[/bold]   {cfg.api_base_url}")
    console.print(f"  [bold]Config Dir:[/bold]     {config_dir}")
    console.print(f"  [bold]Local Skills:[/bold]   {local_dir}  [dim](default)[/dim]")
    console.print(f"  [bold]Global Skills:[/bold]  {global_dir}  [dim](use -g)[/dim]")
    console.print(f"  [bold]Installed:[/bold]      {len(installed)} skill(s)")
    console.print(f"  [bold]Version:[/bold]        {__version__}")
    console.print()


@main.command()
@click.argument('skill_id')
def open(skill_id: str):
    """
    Open skill's source URL in browser.
    
    \b
    Examples:
        skill open notebooklm
        skill open pdf
    """
    import webbrowser
    
    try:
        with SkillMasterAPI() as api:
            skill = None
            
            # Resolve skill ID
            console.print(f"\n[dim]🔍 Looking up skill: {skill_id}...[/dim]")
            
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
                print_error(f"Skill not found: {skill_id}")
                sys.exit(1)
            
            if skill.source_url:
                console.print(f"[green]🌐 Opening: {skill.source_url}[/green]\n")
                webbrowser.open(skill.source_url)
            else:
                print_warning(f"Skill '{skill.name}' has no source URL.")
                sys.exit(1)
                
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: HTTP {e.response.status_code}")
        sys.exit(1)
    except httpx.RequestError as e:
        print_error(f"Connection failed: {e}")
        sys.exit(1)


# Aliases
@main.command('ls', hidden=True)
@click.pass_context
def ls(ctx):
    """Alias for 'list' command"""
    ctx.invoke(list_skills)


@main.command('info', hidden=True)
@click.argument('skill_id')
@click.pass_context
def info(ctx, skill_id: str):
    """Alias for 'show' command"""
    ctx.invoke(show, skill_id=skill_id)


if __name__ == '__main__':
    main()
