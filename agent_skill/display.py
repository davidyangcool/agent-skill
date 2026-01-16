"""
Rich display formatting for Skill CLI
"""

from typing import List, Optional, Callable, Tuple
import json
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich.text import Text
from rich.style import Style
from rich.live import Live

from .models import Skill, InstalledSkill

console = Console()


def _read_key() -> str:
    """Read a single keypress from stdin (cross-platform)"""
    if sys.platform == 'win32':
        import msvcrt
        key = msvcrt.getch()
        if key == b'\xe0':  # Arrow keys prefix on Windows
            key = msvcrt.getch()
            if key == b'H':
                return 'up'
            elif key == b'P':
                return 'down'
            elif key == b'K':
                return 'left'
            elif key == b'M':
                return 'right'
        elif key == b'\r':
            return 'enter'
        elif key == b'q' or key == b'Q':
            return 'q'
        return key.decode('utf-8', errors='ignore')
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':  # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'up'
                    elif ch3 == 'B':
                        return 'down'
                    elif ch3 == 'C':
                        return 'right'
                    elif ch3 == 'D':
                        return 'left'
                return 'escape'
            elif ch == '\r' or ch == '\n':
                return 'enter'
            elif ch == 'q' or ch == 'Q':
                return 'q'
            elif ch == '\x03':  # Ctrl+C
                return 'ctrl+c'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

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


def _build_search_table(skills: List[Skill], query: str, selected_index: int = -1) -> Table:
    """Build the search results table with optional selected row highlighting"""
    from rich import box
    
    table = Table(
        show_header=True,
        header_style="bold white",
        box=box.ROUNDED,
        show_lines=False,
        pad_edge=False,
        collapse_padding=True,
        padding=(0, 1),
    )
    
    table.add_column("Name", style="bold cyan", no_wrap=True, max_width=25)
    # Description color default (white/adaptive)
    table.add_column("Description", no_wrap=True, max_width=60)
    table.add_column("⭐ GitHub", justify="right", style="yellow", no_wrap=True, width=10)
    table.add_column("Rating", justify="left", no_wrap=True, width=12)
    table.add_column("ID", style="dim", no_wrap=True, width=10)

    for i, skill in enumerate(skills):
        rating_display = f"{rating_stars(skill.average_rating)} {skill.average_rating:.1f}"
        github_stars_display = f"{skill.github_stars:,}" if skill.github_stars > 0 else "-"
        
        # Highlight selected row
        if i == selected_index:
            row_style = "reverse"
        else:
            row_style = None
        
        table.add_row(
            skill.name,
            truncate(skill.description or "", 70),
            github_stars_display,
            rating_display,
            skill.id[:8] + "...",
            style=row_style,
        )
    
    return table


def display_search_results(skills: List[Skill], query: str, interactive: bool = True, initial_index: int = 0) -> Tuple[Optional[Skill], int]:
    """
    Display search results in a beautiful table.
    
    Args:
        skills: List of skills to display
        query: The search query
        interactive: If True, enable keyboard navigation (↑/↓ to select, Enter to view, q to quit)
        initial_index: Starting position in the list (for returning to previous position)
    
    Returns:
        Tuple of (Selected Skill or None, selected index)
    """
    if not skills:
        console.print(f"\n[yellow]No skills found matching '[bold]{query}[/bold]'[/yellow]")
        console.print("[dim]Try different keywords or check spelling.[/dim]\n")
        return None, 0
    
    if not interactive or not sys.stdin.isatty():
        # Non-interactive mode: just display the table
        table = _build_search_table(skills, query)
        console.print()
        console.print(table)
        console.print()
        console.print(f"[dim]Found {len(skills)} skill(s). Use [bold]skill show <name>[/bold] for details.[/dim]")

        console.print()
        return None, 0
    
    # Interactive mode - start at initial_index
    selected_index = min(initial_index, len(skills) - 1)
    
    from rich import box
    
    def render_display() -> Panel:
        table = _build_search_table(skills, query, selected_index)
        help_text = "[bold dim]↑/↓: Navigate • Enter: Details • q: Quit[/bold dim]"
        title_text = f"{help_text}   [bold dim]({len(skills)} results)[/bold dim]"
        
        return Panel(
            table,
            title=title_text,
            title_align="center",
            box=box.ROUNDED,
            border_style="dim",
            padding=(0, 1),
        )
    
    try:
        # Use Live with auto_refresh=False to prevent constant updating
        with Live(render_display(), console=console, auto_refresh=False, screen=False) as live:
            live.refresh()  # Initial render
            while True:
                key = _read_key()
                
                if key == 'up':
                    selected_index = (selected_index - 1) % len(skills)
                    live.update(render_display())
                    live.refresh()
                elif key == 'down':
                    selected_index = (selected_index + 1) % len(skills)
                    live.update(render_display())
                    live.refresh()
                elif key == 'enter':
                    return skills[selected_index], selected_index
                elif key == 'q' or key == 'escape' or key == 'ctrl+c':
                    return None, selected_index
    except Exception as e:
        # Fallback to non-interactive mode on any error
        console.print(f"\n[dim]Interactive mode unavailable: {e}[/dim]")
        console.print()
        table = _build_search_table(skills, query)
        console.print(table)
        console.print()
        console.print(f"[dim]Found {len(skills)} skill(s). Use [bold]skill show <name>[/bold] for details.[/dim]")

        console.print()
        return None, 0

def display_skill_detail(skill: Skill, interactive: bool = True, has_back: bool = True) -> Optional[str]:
    """
    Display skill details in a pretty panel.
    
    Args:
        skill: The skill to display
        interactive: If True, wait for user input
        has_back: If True, show "back to results" option (for search context)
    
    Returns:
        'install' if user wants to install, 'back' to return to list, None to quit
    """
    # Build content
    lines = []
    
    lines.append(f"[bold cyan]📦 Name:[/bold cyan]        {skill.name}")
    lines.append(f"[bold cyan]⭐ Rating:[/bold cyan]      {rating_stars(skill.average_rating)} {skill.average_rating:.1f} ({skill.rating_count} votes)")
    # lines.append(f"[bold cyan]📥 Downloads:[/bold cyan]   {skill.download_count:,}")
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
        lines.append(f"[bold cyan]🔗 Source:[/bold cyan]      [blue underline link={skill.source_url}]{skill.source_url}[/blue underline link]")
    
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
    console.print(f"[dim]💡 Install: [bold]skill install {skill.id}[/bold][/dim]")
    console.print(f"[dim]   Or use: [bold]skill install {skill.name}[/bold][/dim]")
    
    # Skill detail page URL
    detail_url = f"{SKILLMASTER_URL}/skill/{skill.id}"
    console.print(f"[dim]🔗 Details:[/dim] [blue underline link={detail_url}]{detail_url}[/blue underline link]")
    

    
    # Interactive mode: wait for user input
    if interactive and sys.stdin.isatty():
        console.print()
        console.print("[bold cyan]───────────────────────────────────────────────────────────────[/bold cyan]")
        if has_back:
            console.print("[dim]  i: Install  |  ←: Back to results  |  Esc/q: Quit[/dim]")
        else:
            console.print("[dim]  i: Install  |  Esc/q: Quit[/dim]")
        console.print("[bold cyan]───────────────────────────────────────────────────────────────[/bold cyan]")
        
        try:
            while True:
                key = _read_key()
                if key == 'i' or key == 'I':
                    return 'install'
                elif key == 'left' and has_back:
                    return 'back'
                elif key == 'q' or key == 'Q' or key == 'escape' or key == 'ctrl+c':
                    return None
        except Exception:
            pass
    
    console.print()
    return None


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
    
    console.print("[bold cyan]Skill Structure:[/bold cyan]")
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


def display_install_step(message: str, icon: str = "◇", style: str = "cyan") -> None:
    """Display a single install step with icon prefix."""
    console.print(f"[{style}]{icon}[/{style}] {message}")


def display_agent_selection(agents: list, selected_ids: list = None, interactive: bool = True) -> list:
    """
    Display agent selection list with checkboxes.
    If interactive, allows ↑/↓ navigation, Space to toggle, Enter to confirm.
    
    Args:
        agents: List of agent dicts with 'id', 'name', 'path' keys
        selected_ids: List of initially selected agent IDs
        interactive: If True, wait for user input to toggle selections
    
    Returns:
        List of selected agent IDs after user confirmation
    """
    if selected_ids is None:
        selected_ids = [a['id'] for a in agents]  # All selected by default
    
    selected = set(selected_ids)
    cursor_index = 0
    
    def render():
        lines = []
        lines.append("[bold]Select agents to install skills to[/bold]")
        lines.append("[dim]↑/↓: Move • Space: Toggle • Enter: Confirm[/dim]")
        for i, agent in enumerate(agents):
            is_selected = agent['id'] in selected
            is_cursor = i == cursor_index
            
            checkbox = "[green]■[/green]" if is_selected else "[dim]□[/dim]"
            cursor_mark = "→ " if is_cursor else "  "
            
            if is_cursor:
                name_style = "bold reverse"
            elif is_selected:
                name_style = "bold"
            else:
                name_style = "dim"
            
            lines.append(f"  {cursor_mark}{checkbox} [{name_style}]{agent['name']}[/{name_style}] [dim]({agent['path']})[/dim]")
        return "\n".join(lines)
    
    if not interactive or not sys.stdin.isatty():
        console.print(render())
        return list(selected)
    
    # Interactive selection with Live display
    from rich.live import Live
    from rich.text import Text
    
    try:
        with Live(Text.from_markup(render()), console=console, auto_refresh=False, screen=False) as live:
            live.refresh()
            while True:
                key = _read_key()
                
                if key == 'up':
                    cursor_index = (cursor_index - 1) % len(agents)
                    live.update(Text.from_markup(render()))
                    live.refresh()
                elif key == 'down':
                    cursor_index = (cursor_index + 1) % len(agents)
                    live.update(Text.from_markup(render()))
                    live.refresh()
                elif key == ' ':
                    # Toggle selection
                    agent_id = agents[cursor_index]['id']
                    if agent_id in selected:
                        selected.discard(agent_id)
                    else:
                        selected.add(agent_id)
                    live.update(Text.from_markup(render()))
                    live.refresh()
                elif key == 'enter':
                    # Confirm selection
                    if not selected:
                        # Must select at least one
                        continue
                    break
                elif key == 'q' or key == 'escape' or key == 'ctrl+c':
                    # Cancel
                    return []
    except Exception:
        console.print(render())
    
    return list(selected)


def display_install_summary(skill_name: str, install_results: list) -> None:
    """
    Display final installation summary.
    
    Args:
        skill_name: Name of the installed skill
        install_results: List of dicts with 'agent_name', 'path', 'success' keys
    """
    console.print()
    console.print(f"[bold green]Successfully installed {skill_name}![/bold green]")
    console.print()
    for result in install_results:
        if result['success']:
            console.print(f"  [green]✓[/green] [bold]{result['agent_name']}[/bold]: [dim]{result['path']}[/dim]")
        else:
            console.print(f"  [red]✗[/red] [bold]{result['agent_name']}[/bold]: [red]Failed[/red]")
    console.print()


# Path needs import
from pathlib import Path
