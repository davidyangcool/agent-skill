"""
Rich display formatting for Skill CLI
"""

from typing import List, Optional
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich.text import Text
from rich.style import Style

from .models import Skill, InstalledSkill

console = Console()

# Website promotion message
SKILLMASTER_URL = "https://skillmaster.cc"
PROMOTION_MSG = f"[dim]🌐 Discover more agent skills: [link={SKILLMASTER_URL}]{SKILLMASTER_URL}[/link][/dim]"


def rating_stars(rating: float, max_stars: int = 5) -> str:
    """Convert rating to star display"""
    full_stars = int(rating)
    half_star = rating - full_stars >= 0.5
    empty_stars = max_stars - full_stars - (1 if half_star else 0)
    
    return "★" * full_stars + ("½" if half_star else "") + "☆" * empty_stars


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def display_search_results(skills: List[Skill], query: str) -> None:
    """Display search results in a beautiful table"""
    if not skills:
        console.print(f"\n[yellow]No skills found matching '[bold]{query}[/bold]'[/yellow]")
        console.print("[dim]Try different keywords or check spelling.[/dim]\n")
        return
    
    table = Table(
        title=f"🔍 Search Results: \"{query}\"",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    
    table.add_column("Name", style="bold green", no_wrap=True, max_width=25)
    table.add_column("Description", no_wrap=True, max_width=45)
    table.add_column("Rating", justify="center", no_wrap=True, width=14)
    table.add_column("Downloads", justify="right", no_wrap=True, width=10)
    table.add_column("ID", style="dim", no_wrap=True, width=10)

    
    for skill in skills:
        rating_display = f"{rating_stars(skill.average_rating)} {skill.average_rating:.1f}"
        
        table.add_row(
            skill.name,
            truncate(skill.description or "", 50),
            rating_display,
            f"{skill.download_count:,}",
            skill.id[:8] + "...",
        )
    
    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Found {len(skills)} skill(s). Use [bold]skill show <name>[/bold] for details.[/dim]")
    console.print(PROMOTION_MSG)
    console.print()


def display_skill_detail(skill: Skill) -> None:
    """Display skill details in a pretty panel"""
    # Build content
    lines = []
    
    lines.append(f"[bold cyan]📦 Name:[/bold cyan]        {skill.name}")
    lines.append(f"[bold cyan]⭐ Rating:[/bold cyan]      {rating_stars(skill.average_rating)} {skill.average_rating:.1f} ({skill.rating_count} votes)")
    lines.append(f"[bold cyan]📥 Downloads:[/bold cyan]   {skill.download_count:,}")
    lines.append(f"[bold cyan]💬 Comments:[/bold cyan]    {skill.comment_count}")
    lines.append(f"[bold cyan]📚 Tutorials:[/bold cyan]   {skill.tutorial_count}")
    
    if skill.github_stars > 0:
        lines.append(f"[bold cyan]⭐ GitHub:[/bold cyan]      {skill.github_stars:,} stars")
    
    if skill.file_size_mb > 0:
        lines.append(f"[bold cyan]📁 Size:[/bold cyan]        {skill.file_size_mb:.2f} MB")
    
    # Tags
    if skill.tags:
        tag_names = ", ".join(f"#{t.name}" for t in skill.tags)
        lines.append(f"[bold cyan]🏷️  Tags:[/bold cyan]        {tag_names}")
    
    # Source URL
    if skill.source_url:
        # Keep full URL for clickable links
        lines.append(f"[bold cyan]🔗 Source:[/bold cyan]      [link={skill.source_url}]{skill.source_url}[/link]")
    
    # Description
    if skill.description:
        lines.append("")
        lines.append("[bold cyan]📄 Description:[/bold cyan]")
        lines.append(f"   {skill.description}")
    
    content = "\n".join(lines)
    
    panel = Panel(
        content,
        title=f"[bold white]{skill.name}[/bold white]",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )
    
    console.print()
    console.print(panel)
    
    # Directory structure
    if skill.directory_structure:
        try:
            dir_data = json.loads(skill.directory_structure) if isinstance(skill.directory_structure, str) else skill.directory_structure
            if dir_data and "root" in dir_data:
                console.print()
                display_directory_tree(dir_data, skill.name)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Install hint
    console.print()
    short_id = skill.id[:8]
    console.print(f"[dim]💡 Install: [bold]skill install {skill.id}[/bold][/dim]")
    console.print(f"[dim]   Or use: [bold]skill install {skill.name}[/bold][/dim]")
    
    # Skill detail page URL
    detail_url = f"{SKILLMASTER_URL}/skill/{skill.id}"
    console.print(f"[dim]🔗 Details: [link={detail_url}]{detail_url}[/link][/dim]")
    
    console.print(PROMOTION_MSG)
    console.print()


def display_directory_tree(dir_data: dict, name: str = "root") -> None:
    """Display directory structure as a tree"""
    # dir_data format: {"root": "skill_name", "children": [...]}
    root_name = dir_data.get("root", name)
    children = dir_data.get("children", [])
    
    tree = Tree(f"📂 [bold]{root_name}[/bold]", guide_style="dim")
    
    def add_children(parent_tree: Tree, items: list):
        for child in items:
            if child.get("type") == "directory":
                child_tree = parent_tree.add(f"📁 [bold]{child['name']}[/bold]")
                if "children" in child:
                    add_children(child_tree, child["children"])
            else:
                size_str = ""
                if "size" in child and child["size"]:
                    size_kb = child["size"] / 1024
                    size_str = f" [dim]({size_kb:.1f} KB)[/dim]"
                parent_tree.add(f"📄 {child['name']}{size_str}")
    
    if children:
        add_children(tree, children)
    
    console.print("[bold cyan]📂 Package Structure:[/bold cyan]")
    console.print(tree)


def display_installed_list(skills: List[InstalledSkill]) -> None:
    """Display list of installed skills"""
    if not skills:
        console.print("\n[yellow]No skills installed yet.[/yellow]")
        console.print("[dim]Use [bold]skill install <name>[/bold] to install a skill.[/dim]\n")
        return
    
    table = Table(
        title="📦 Installed Skills",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        expand=True,
    )
    
    table.add_column("Name", style="bold green", max_width=30)
    table.add_column("Installed At", width=20)
    table.add_column("Path", style="dim")
    table.add_column("ID (short)", style="dim", width=12)
    
    for skill in skills:
        # Format date
        date_str = skill.installed_at[:10] if skill.installed_at else "Unknown"
        
        # Shorten path for display
        short_path = skill.path.replace(str(Path.home()), "~") if skill.path else ""
        
        table.add_row(
            skill.name,
            date_str,
            short_path,
            skill.id[:8] + "..." if skill.id else "",
        )
    
    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Total: {len(skills)} skill(s) installed.[/dim]")
    console.print(PROMOTION_MSG)
    console.print()


def get_download_progress() -> Progress:
    """Create a download progress bar"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    )


def print_success(message: str) -> None:
    """Print a success message"""
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_error(message: str) -> None:
    """Print an error message"""
    console.print(f"[bold red]❌ {message}[/bold red]")


def print_info(message: str) -> None:
    """Print an info message"""
    console.print(f"[cyan]ℹ️  {message}[/cyan]")


def print_warning(message: str) -> None:
    """Print a warning message"""
    console.print(f"[yellow]⚠️  {message}[/yellow]")


# Path needs import
from pathlib import Path
