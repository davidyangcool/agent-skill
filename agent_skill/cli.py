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
def search(query: str, limit: int):
    """
    Search for skills by keywords.
    
    \b
    Examples:
        skill search document
        skill search "python automation"
        skill search pdf --limit 10
    """
    console.print(f"\n[dim]🔍 Searching for '[bold]{query}[/bold]'...[/dim]")
    
    try:
        with SkillMasterAPI() as api:
            skills = api.search(query)
            
            # Limit results
            if len(skills) > limit:
                skills = skills[:limit]
            
            display_search_results(skills, query)
            
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: HTTP {e.response.status_code}")
        if e.response.status_code == 500:
            print_info("The server encountered an error. Try again later.")
        sys.exit(1)
    except httpx.RequestError as e:
        print_error(f"Connection failed: {e}")
        print_info("Check your internet connection or API server availability.")
        sys.exit(1)


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
                display_skill_detail(skill)
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
@click.option('--global', '-g', 'global_install', is_flag=True, help='Install to global directory (~/.claude/skills).')
@click.option('--path', '-p', type=click.Path(), help='Custom installation path.')
@click.option('--force', '-f', is_flag=True, help='Overwrite if already installed.')
def install(skill_id: str, global_install: bool, path: Optional[str], force: bool):
    """
    Download and install a skill.
    
    \b
    By default, installs to ./.claude/skills/ (local project directory).
    Use -g/--global to install to ~/.claude/skills/ (global directory).
    
    \b
    SKILL_ID can be:
      - Full SHA-256 ID (64 characters)
      - Skill name (will search first)
    
    \b
    Examples:
        skill install docs-generator          # Install to ./.claude/skills/
        skill install pdf-processor -g        # Install to ~/.claude/skills/
        skill install my-skill --path ./dir/  # Install to custom path
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
            
            console.print(f"[green]📦 Found: {skill.name}[/green]")
            
            # Check if already installed
            existing = get_installed_skill(skill.name)
            if existing and not force:
                print_warning(f"Skill '{skill.name}' is already installed.")
                print_info(f"Use --force to reinstall or skill uninstall {skill.name} first.")
                sys.exit(1)
            
            # Determine install path
            if path:
                install_dir = Path(path).expanduser() / skill.name
            else:
                install_dir = get_skills_dir(global_install=global_install) / skill.name
            
            # Create temp download path
            temp_zip = install_dir.parent / f".{skill.name}.zip.tmp"
            
            # Download with progress
            console.print(f"[dim]📥 Downloading to {temp_zip}...[/dim]")
            
            with get_download_progress() as progress:
                task = progress.add_task(f"Downloading {skill.name}", total=None)
                
                def update_progress(downloaded: int, total: int):
                    if total > 0:
                        progress.update(task, total=total, completed=downloaded)
                    else:
                        progress.update(task, advance=downloaded)
                
                try:
                    api.download_skill_with_progress(skill.id, temp_zip, update_progress)
                except httpx.HTTPStatusError as e:
                    progress.stop()
                    print_error(f"Download failed: HTTP {e.response.status_code}")
                    if temp_zip.exists():
                        temp_zip.unlink()
                    sys.exit(1)
            
            # Extract ZIP
            console.print(f"[dim]📂 Extracting to {install_dir}...[/dim]")
            
            # Remove existing directory if force
            if install_dir.exists():
                shutil.rmtree(install_dir)
            
            install_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                with zipfile.ZipFile(temp_zip, 'r') as zf:
                    # Extract all files
                    zf.extractall(install_dir)
            except zipfile.BadZipFile:
                print_error("Downloaded file is not a valid ZIP archive.")
                if temp_zip.exists():
                    temp_zip.unlink()
                sys.exit(1)
            
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
            
            print_success(f"Successfully installed {skill.name}!")
            console.print(f"\n[dim]📂 Location: [bold]{install_dir}[/bold][/dim]\n")
            
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
