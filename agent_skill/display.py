"""
Rich display formatting for Skill CLI
"""

from typing import List, Optional, Callable, Tuple, Any
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
from rich.layout import Layout
from rich.console import Group, ConsoleOptions, RenderResult
from rich.padding import Padding
from rich.align import Align
from rich import box
import io

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
        except:
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _get_render_height(console: Console, renderable: Any, width: int) -> int:
    """Helper to measure the height of a renderable given a width."""
    # Create a dummy console to measure
    dummy = Console(width=width, file=io.StringIO())
    with dummy.capture() as capture:
        dummy.print(renderable)
    return len(capture.get().splitlines())

# Website promotion message
SKILLMASTER_URL = "https://skillmaster.cc"
PROMOTION_MSG = f"[dim]🌐 Discover more agent skills: [link={SKILLMASTER_URL}]{SKILLMASTER_URL}[/link][/dim]"


def rating_stars(rating: float, max_stars: int = 5) -> str:
    """Convert rating to star display using ⭐ emoji (rounded up)"""
    import math
    num_stars = math.ceil(rating)
    return "⭐" * num_stars


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def _render_status_bar(text: str) -> Padding:
    """Render a full-width status bar with inverted colors"""
    # Use Padding with expand=True to fill width, and Align to center text
    return Padding(
        Align.center(
             Text(f" {text} ", style="bold white on cyan")
        ),
        (0, 0),
        style="bold white on cyan",
        expand=True
    )


def _render_footer(text: str) -> Panel:
    """Render a consistent footer with keyboard shortcuts"""
    return Panel(
        Text(text, justify="center", style="black on cyan"),
        style="cyan",
        box=box.ROUNDED,
        padding=0
    )


def _build_search_table(skills: List[Skill], query: str, selected_index: int = -1) -> Table:
    """Build the search results table with optional selected row highlighting"""
    table = Table(
        show_header=True,
        header_style="bold white",
        box=box.SIMPLE,
        show_lines=False,
        pad_edge=False,
        collapse_padding=True,
        padding=(0, 1),
        expand=True,
    )
    
    # Pointer column - minimal width
    table.add_column("", width=2, no_wrap=True)
    table.add_column("Name", style="bold cyan", no_wrap=True, max_width=30)
    table.add_column("Description", no_wrap=True, ratio=1)
    table.add_column("GitHub⭐", justify="right", style="yellow", no_wrap=True, width=10)
    table.add_column("Rating", justify="left", no_wrap=True, width=14)

    for i, skill in enumerate(skills):
        rating_display = f"{rating_stars(skill.average_rating)} {skill.average_rating:.1f}"
        github_stars_display = f"{skill.github_stars:,}" if skill.github_stars > 0 else "-"
        
        # Highlight selected row
        if i == selected_index:
            pointer = "➤"
            name_style = "bold cyan"
            desc_style = "white"
            row_style = "on struct" # distinct background if theme supports, otherwise simple
            # Using simple bold highlighing
        else:
            pointer = " "
            name_style = "cyan"
            desc_style = "dim"
            row_style = None
            
        table.add_row(
            Text(pointer, style="bold magenta" if i == selected_index else ""),
            Text(skill.name, style=name_style),
            Text(truncate(skill.description or "", 80), style=desc_style),
            github_stars_display,
            rating_display,
            style="on grey23" if i == selected_index else None
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
    
    
    def render_display() -> Group:
        table = _build_search_table(skills, query, selected_index)
        
        # Main content panel
        main_panel = Panel(
            table,
            title=f"[bold cyan]Search Results: {query}[/bold cyan] ({len(skills)})",
            title_align="left",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 0),
        )
        
        # Footer
        help_text = "↑/↓: Navigate • Enter: Details • q: Quit"
        
        return Group(main_panel, _render_status_bar(help_text))
    
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
    Display skill details in a dual-column layout.
    """
    # --- Prepare Left Column (Metadata) ---
    meta_rows = []
    
    # Rating (Single Line)
    meta_rows.append(f"[bold]Rating:[/bold] {rating_stars(skill.average_rating)} {skill.average_rating:.1f} ({skill.rating_count})")
    
    # Stats
    stats = []
    if skill.github_stars > 0:
        stats.append(f"⭐ {skill.github_stars:,} github stars")
    if skill.file_size_mb > 0:
        stats.append(f"📦 {skill.file_size_mb:.2f} MB")
    if stats:
        meta_rows.append("\n".join(stats))
        
    # Tags - blue underline links
    if skill.tags:
        tag_links = []
        for t in skill.tags:
            tag_links.append(f"[blue underline link=https://skillmaster.cc/tag/{t.id}]#{t.name}[/blue underline link]")
        meta_rows.append("\n".join(tag_links))

    # Links (Source | Detail)
    links = []
    if skill.source_url:
        links.append(f"[blue underline link={skill.source_url}]🔗 Source[/blue underline link]")
    
    detail_url = f"https://skillmaster.cc/skill/{skill.id}"
    links.append(f"[blue underline link={detail_url}]🌐 Detail[/blue underline link]")
    
    meta_rows.append("  |  ".join(links))
        
    # Metadata Table inside Panel
    meta_table = Table.grid(padding=(0, 0)) # Reduced padding
    for i, row in enumerate(meta_rows):
        meta_table.add_row(row)
        # Add spacer only if not the last item
        if i < len(meta_rows) - 1:
            meta_table.add_row("") 
        
    # Combine Meta (Install panel removed as per request)
    left_group = Group(
        meta_table
    )

    # --- Prepare Right Column Content (Before Alignment) ---
    
    # 1. Description Content
    desc_lines = []
    desc_lines.append(Text(skill.description or "No description.", style="white"))
    desc_lines.append(Text(""))
    # Links are in left column now

    # 2. Structure Content
    structure_renderable = Text("[dim]No structure data available.[/dim]")
    
    if skill.directory_structure:
        try:
            dir_data = json.loads(skill.directory_structure) if isinstance(skill.directory_structure, str) else skill.directory_structure
            if dir_data and "root" in dir_data:
                MAX_PREVIEW_LINES = 10
                current_lines = 0
                total_files = 0
                
                def count_files(items):
                    count = 0
                    for item in items:
                        count += 1
                        if "children" in item: count += count_files(item["children"])
                    return count
                
                total_files = count_files(dir_data.get("children", []))
                root_name = dir_data.get("root", skill.name)
                tree = Tree(f"📂 [bold]{root_name}[/bold]", guide_style="dim")
                
                def add_children_limited(parent_tree: Tree, items: list):
                    nonlocal current_lines
                    for i, child in enumerate(items):
                        if current_lines >= MAX_PREVIEW_LINES:
                            remaining = total_files - current_lines
                            parent_tree.add(f"[dim]🔒 ... {remaining} more files[/dim]")
                            return False
                        current_lines += 1
                        
                        if child.get("type") == "directory":
                            if current_lines >= MAX_PREVIEW_LINES:
                                remaining = total_files - current_lines
                                parent_tree.add(f"[dim]🔒 ... {remaining} more files[/dim]")
                                return False
                            child_tree = parent_tree.add(f"📁 [bold]{child['name']}[/bold]")
                            if "children" in child:
                                if not add_children_limited(child_tree, child["children"]): return False
                        else:
                            parent_tree.add(f"📄 {child['name']}")
                    return True

                children = dir_data.get("children", [])
                if children:
                    add_children_limited(tree, children)
                    
                structure_renderable = tree
        except:
             pass
    
    # --- Dynamic Alignment Logic ---
    # Calculate column widths based on 3:7 ratio
    # Total available width approx console.width - padding
    
    total_width = console.width - 4 
    left_width = int(total_width * 0.3) - 4 
    right_width = int(total_width * 0.7) - 4 
    
    # Measure heights 
    # Overhead calculation:
    # Panel with box.ROUNDED has 2 lines of border (top/bottom)
    # padding=(1, 1) adds 1 line top + 1 line bottom = 2 lines
    # Total overhead for padding=(1,1) is 4 lines.
    # Total overhead for padding=(0,1) is 2 lines (borders only, no vertical padding).
    
    h_left_content = _get_render_height(console, left_group, left_width)
    h_left_req = h_left_content + 4 # padding=(1,1)
    
    h_desc_content = _get_render_height(console, Group(*desc_lines), right_width)
    h_desc_req = h_desc_content + 4 # padding=(1,1)
    
    h_struct_content = _get_render_height(console, structure_renderable, right_width)
    h_struct_req = h_struct_content + 2 # padding=(0,1)
    
    h_right_stack_req = h_desc_req + h_struct_req
    
    # Identify target height (max of both columns). This is the height of the entire row.
    target_height = max(h_left_req, h_right_stack_req)
    
    # Adjust Panels
    # Left Panel
    left_panel = Panel(
        left_group,
        title="[dim]Metadata[/dim]",
        title_align="left", 
        border_style="dim",
        box=box.ROUNDED,
        padding=(1, 1),
        height=target_height # Explicit height matches the taller column
    )
    
    # Right Panels
    desc_panel = Panel(
        Group(*desc_lines),
        title="[dim]Description[/dim]",
        title_align="left",
        border_style="dim",
        box=box.ROUNDED,
        padding=(1, 1)
        # natural height (measured as h_desc_req)
    )
    
    # Structure Panel takes EXACTLY the remaining space
    # Total Right Height = desc_panel height + structure_panel height
    # structure_panel height = target_height - desc_panel height
    
    structure_height_target = target_height - h_desc_req
    
    structure_panel = Panel(
        structure_renderable,
        title="[dim]Structure Preview[/dim]",
        title_align="left",
        border_style="dim",
        box=box.ROUNDED,
        padding=(0, 1),
        height=structure_height_target # Accurate fill
    )
    
    right_content = [desc_panel, structure_panel]

    # --- Layout Assembly ---
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=3) # Left
    grid.add_column(ratio=7) # Right
    
    # Right side group
    right_group = Group(*right_content)
    
    grid.add_row(left_panel, right_group)
    
    # Main Outer Panel for "Skill Details: <name>"
    main_frame = Panel(
        grid,
        title=f"[bold cyan]Skill Details: {skill.name}[/bold cyan]",
        title_align="left",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1)
    )

    # Footer - removed 'v: View Files'
    shortcuts = "i: Install • q: Quit"
    if has_back:
        shortcuts = "i: Install • ←: Back • q: Quit"
    
    final_view = Group(
        main_frame,
        _render_status_bar(shortcuts)
    )
    
    # --- Interactive Loop ---
    if interactive and sys.stdin.isatty():
        try:
            # Use Live to show the display
            with Live(final_view, console=console, auto_refresh=False, screen=False) as live:
                live.refresh()
                while True:
                    key = _read_key()
                    if key == 'i' or key == 'I':
                        return 'install'
                    elif key == 'left' and has_back:
                        return 'back'
                    elif key == 'q' or key == 'Q' or key == 'escape' or key == 'ctrl+c':
                        return None
        except Exception:
            # Fallback
            console.print(grid)
            return None
    else:
        console.print(grid)
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
    Display agent selection list with checkboxes in a Panel.
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
        for i, agent in enumerate(agents):
            is_selected = agent['id'] in selected
            is_cursor = i == cursor_index
            
            checkbox = "[cyan]■[/cyan]" if is_selected else "[dim]□[/dim]"
            cursor_mark = "→ " if is_cursor else "  "
            
            if is_cursor:
                name_style = "bold reverse"
            elif is_selected:
                name_style = "bold"
            else:
                name_style = "dim"
            
            lines.append(f"{cursor_mark}{checkbox} [{name_style}]{agent['name']}[/{name_style}]")
        
        content = "\n".join(lines)
        
        main_panel = Panel(
            content,
            title="[bold cyan]Select Agents[/bold cyan]",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
        return Group(main_panel, _render_status_bar("↑/↓: Move • Space: Toggle • Enter: Confirm"))
    
    if not interactive or not sys.stdin.isatty():
        console.print()
        console.print(render())
        return list(selected)
    
    # Interactive selection with Live display
    from rich.live import Live
    
    try:
        console.print()
        with Live(render(), console=console, auto_refresh=False, screen=False) as live:
            live.refresh()
            while True:
                key = _read_key()
                
                if key == 'up':
                    cursor_index = (cursor_index - 1) % len(agents)
                    live.update(render())
                    live.refresh()
                elif key == 'down':
                    cursor_index = (cursor_index + 1) % len(agents)
                    live.update(render())
                    live.refresh()
                elif key == ' ':
                    # Toggle selection
                    agent_id = agents[cursor_index]['id']
                    if agent_id in selected:
                        selected.discard(agent_id)
                    else:
                        selected.add(agent_id)
                    live.update(render())
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


def display_scope_selection(interactive: bool = True) -> str:
    """
    Display installation scope selection (Project or Global) in a Panel.
    Radio-button style selection (only one can be selected).
    
    Returns:
        'project' or 'global', or empty string if cancelled
    """
    scopes = [
        {"id": "project", "name": "Project", "desc": "Install in current project directory"},
        {"id": "global", "name": "Global", "desc": "Install in home directory"},
    ]
    
    selected_index = 0  # Default to Project
    
    def render():
        lines = []
        for i, scope in enumerate(scopes):
            is_selected = i == selected_index
            radio = "[cyan]●[/cyan]" if is_selected else "[dim]○[/dim]"
            name_style = "bold" if is_selected else "dim"
            lines.append(f"{radio} [{name_style}]{scope['name']}[/{name_style}] [dim]({scope['desc']})[/dim]")
        
        content = "\n".join(lines)
        
        main_panel = Panel(
            content,
            title="[bold cyan]Installation Scope[/bold cyan]",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
        return Group(main_panel, _render_status_bar("↑/↓: Move • Enter: Confirm"))
    
    if not interactive or not sys.stdin.isatty():
        console.print()
        console.print(render())
        return scopes[selected_index]["id"]
    
    from rich.live import Live
    
    try:
        console.print()
        with Live(render(), console=console, auto_refresh=False, screen=False) as live:
            live.refresh()
            while True:
                key = _read_key()
                
                if key == 'up':
                    selected_index = (selected_index - 1) % len(scopes)
                    live.update(render())
                    live.refresh()
                elif key == 'down':
                    selected_index = (selected_index + 1) % len(scopes)
                    live.update(render())
                    live.refresh()
                elif key == 'enter':
                    break
                elif key == 'q' or key == 'escape':
                    return ""
    except Exception:
        console.print(render())
    
    return scopes[selected_index]["id"]


def display_install_summary(skill_name: str, install_results: list, source_url: str = None) -> None:
    """
    Display final installation summary in a Panel.
    
    Args:
        skill_name: Name of the installed skill
        install_results: List of dicts with 'agent_name', 'path', 'success' keys
        source_url: Optional source URL for the skill
    """
    lines = []
    lines.append(f"[bold cyan]Successfully installed {skill_name}![/bold cyan]")
    lines.append("")
    
    for result in install_results:
        if result['success']:
            lines.append(f"[green]✓[/green] [bold]{result['agent_name']}[/bold]: [blue]{result['path']}[/blue]")
        else:
            lines.append(f"[red]✗[/red] [bold]{result['agent_name']}[/bold]: [red]Failed[/red]")
    
    # Add promotion link
    lines.append("")
    lines.append(f"[dim]Discover more skills at[/dim] [bold blue underline]https://skillmaster.cc[/bold blue underline]")
    
    content = "\n".join(lines)
    
    panel = Panel(
        content,
        title=f"[bold cyan]Installed {skill_name}[/bold cyan]",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )
    
    console.print()
    console.print(panel)


def display_download_panel(skill_name: str, progress_renderable, source_url: str = None) -> Panel:
    """
    Create a Panel with download progress bar and source URL inside.
    
    Args:
        skill_name: Name of the skill being downloaded
        progress_renderable: The Rich progress renderable
        source_url: Optional source URL for the skill
    
    Returns:
        A Panel containing the progress bar and source URL
    """
    from rich.console import Group
    from rich.text import Text
    
    if source_url:
        content = Group(
            Text.from_markup(f"[bold cyan]Source:[/bold cyan] [blue underline]{source_url}[/blue underline]"),
            Text(""),
            progress_renderable
        )
    else:
        content = progress_renderable
    
    return Panel(
        content,
        title=f"[bold cyan]Downloading {skill_name}[/bold cyan]",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )


# Path needs import
from pathlib import Path
